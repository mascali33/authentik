package application

import (
	"context"
	"crypto/tls"
	"encoding/gob"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"

	"github.com/coreos/go-oidc"
	"github.com/gorilla/mux"
	"github.com/gorilla/sessions"
	"github.com/prometheus/client_golang/prometheus"
	log "github.com/sirupsen/logrus"
	"goauthentik.io/api"
	"goauthentik.io/internal/outpost/ak"
	"goauthentik.io/internal/outpost/proxyv2/constants"
	"goauthentik.io/internal/outpost/proxyv2/hs256"
	"goauthentik.io/internal/outpost/proxyv2/metrics"
	"goauthentik.io/internal/utils/web"
	"golang.org/x/oauth2"
)

type Application struct {
	Host                 string
	Cert                 *tls.Certificate
	UnauthenticatedRegex []*regexp.Regexp

	endpint       OIDCEndpoint
	oauthConfig   oauth2.Config
	tokenVerifier *oidc.IDTokenVerifier

	sessions    sessions.Store
	proxyConfig api.ProxyOutpostConfig
	httpClient  *http.Client

	log *log.Entry
	mux *mux.Router
}

func NewApplication(p api.ProxyOutpostConfig, c *http.Client, cs *ak.CryptoStore, akHost string) *Application {
	gob.Register(Claims{})

	externalHost, err := url.Parse(p.ExternalHost)
	if err != nil {
		log.WithError(err).Warning("Failed to parse URL, skipping provider")
	}

	// Support for RS256, new proxy providers will use HS256 but old ones
	// might not, and this makes testing easier
	var ks oidc.KeySet
	if contains(p.OidcConfiguration.IdTokenSigningAlgValuesSupported, "HS256") {
		ks = hs256.NewKeySet(*p.ClientSecret)
	} else {
		ctx := context.WithValue(context.Background(), oauth2.HTTPClient, c)
		oidc.NewRemoteKeySet(ctx, p.OidcConfiguration.JwksUri)
	}

	var verifier = oidc.NewVerifier(p.OidcConfiguration.Issuer, ks, &oidc.Config{
		ClientID:             *p.ClientId,
		SupportedSigningAlgs: []string{"HS256"},
	})

	// Configure an OpenID Connect aware OAuth2 client.
	endpoint := GetOIDCEndpoint(p, akHost)
	oauth2Config := oauth2.Config{
		ClientID:     *p.ClientId,
		ClientSecret: *p.ClientSecret,
		RedirectURL:  urlJoin(p.ExternalHost, "/akprox/callback"),
		Endpoint:     endpoint.Endpoint,
		Scopes:       []string{oidc.ScopeOpenID, "profile", "email", "ak_proxy"},
	}
	mux := mux.NewRouter()
	a := &Application{
		Host:          externalHost.Host,
		log:           log.WithField("logger", "authentik.outpost.proxy.bundle").WithField("provider", p.Name),
		endpint:       endpoint,
		oauthConfig:   oauth2Config,
		tokenVerifier: verifier,
		sessions:      GetStore(p),
		proxyConfig:   p,
		httpClient:    c,
		mux:           mux,
	}
	muxLogger := log.WithField("logger", "authentik.outpost.proxyv2.application").WithField("name", p.Name)
	mux.Use(web.NewLoggingHandler(muxLogger, func(l *log.Entry, r *http.Request) *log.Entry {
		s, err := a.sessions.Get(r, constants.SeesionName)
		if err != nil {
			return l
		}
		claims, ok := s.Values[constants.SessionClaims]
		if claims == nil || !ok {
			return l
		}
		c, ok := claims.(Claims)
		if !ok {
			return l
		}
		return l.WithField("request_username", c.Email)
	}))
	mux.Use(func(inner http.Handler) http.Handler {
		return http.HandlerFunc(func(rw http.ResponseWriter, r *http.Request) {
			c, _ := a.getClaims(r)
			user := ""
			if c != nil {
				user = c.Email
			}
			before := time.Now()
			inner.ServeHTTP(rw, r)
			after := time.Since(before)
			metrics.Requests.With(prometheus.Labels{
				"type":   "app",
				"scheme": r.URL.Scheme,
				"method": r.Method,
				"path":   r.URL.Path,
				"host":   web.GetHost(r),
				"user":   user,
			}).Observe(float64(after))
		})
	})

	// Support /start and /sign_in for backwards compatibility
	mux.HandleFunc("/akprox/start", a.handleRedirect)
	mux.HandleFunc("/akprox/sign_in", a.handleRedirect)
	mux.HandleFunc("/akprox/callback", a.handleCallback)
	mux.HandleFunc("/akprox/sign_out", a.handleSignOut)
	switch *p.Mode {
	case api.PROXYMODE_PROXY:
		err = a.configureProxy()
	case api.PROXYMODE_FORWARD_SINGLE:
		fallthrough
	case api.PROXYMODE_FORWARD_DOMAIN:
		err = a.configureForward()
	}
	if err != nil {
		a.log.WithError(err).Warning("failed to configure mode")
	}

	if kp := p.Certificate.Get(); kp != nil {
		err := cs.AddKeypair(*kp)
		if err != nil {
			a.log.WithError(err).Warning("Failed to initially fetch certificate")
		}
		a.Cert = cs.Get(*kp)
	}

	if *p.SkipPathRegex != "" {
		a.UnauthenticatedRegex = make([]*regexp.Regexp, 0)
		for _, regex := range strings.Split(*p.SkipPathRegex, "\n") {
			re, err := regexp.Compile(regex)
			if err != nil {
				// TODO: maybe create event for this?
				a.log.WithError(err).Warning("failed to compile regex")
			} else {
				a.UnauthenticatedRegex = append(a.UnauthenticatedRegex, re)
			}
		}
	}
	return a
}

func (a *Application) IsAllowlisted(r *http.Request) bool {
	for _, u := range a.UnauthenticatedRegex {
		if u.MatchString(r.URL.Path) {
			return true
		}
	}
	return false
}

func (a *Application) Mode() api.ProxyMode {
	return *a.proxyConfig.Mode
}

func (a *Application) ServeHTTP(rw http.ResponseWriter, r *http.Request) {
	a.mux.ServeHTTP(rw, r)
}

func (a *Application) handleSignOut(rw http.ResponseWriter, r *http.Request) {
	// TODO: Token revocation
	s, err := a.sessions.Get(r, constants.SeesionName)
	if err != nil {
		http.Redirect(rw, r, a.endpint.EndSessionEndpoint, http.StatusFound)
		return
	}
	s.Options.MaxAge = -1
	err = s.Save(r, rw)
	if err != nil {
		http.Redirect(rw, r, a.endpint.EndSessionEndpoint, http.StatusFound)
		return
	}
	http.Redirect(rw, r, a.endpint.EndSessionEndpoint, http.StatusFound)
}
