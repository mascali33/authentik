"""authentik OAuth2 OpenID Userinfo views"""
from typing import Any, Optional

from deepmerge import always_merger
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBadRequest
from django.views import View
from structlog.stdlib import get_logger

from authentik.core.exceptions import PropertyMappingExpressionException
from authentik.events.models import Event, EventAction
from authentik.providers.oauth2.constants import (
    SCOPE_GITHUB_ORG_READ,
    SCOPE_GITHUB_USER,
    SCOPE_GITHUB_USER_EMAIL,
    SCOPE_GITHUB_USER_READ,
)
from authentik.providers.oauth2.models import RefreshToken, ScopeMapping
from authentik.providers.oauth2.utils import TokenResponse, cors_allow

LOGGER = get_logger()


class UserInfoView(View):
    """Create a dictionary with all the requested claims about the End-User.
    See: http://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse"""

    token: Optional[RefreshToken]

    def get_scope_descriptions(self, scopes: list[str]) -> list[dict[str, str]]:
        """Get a list of all Scopes's descriptions"""
        scope_descriptions = []
        for scope in ScopeMapping.objects.filter(scope_name__in=scopes).order_by("scope_name"):
            if scope.description != "":
                scope_descriptions.append({"id": scope.scope_name, "name": scope.description})
        # GitHub Compatibility Scopes are handeled differently, since they required custom paths
        # Hence they don't exist as Scope objects
        github_scope_map = {
            SCOPE_GITHUB_USER: ("GitHub Compatibility: Access your User Information"),
            SCOPE_GITHUB_USER_READ: ("GitHub Compatibility: Access your User Information"),
            SCOPE_GITHUB_USER_EMAIL: ("GitHub Compatibility: Access you Email addresses"),
            SCOPE_GITHUB_ORG_READ: ("GitHub Compatibility: Access your Groups"),
        }
        for scope in scopes:
            if scope in github_scope_map:
                scope_descriptions.append({"id": scope, "name": github_scope_map[scope]})
        return scope_descriptions

    def get_claims(self, token: RefreshToken) -> dict[str, Any]:
        """Get a dictionary of claims from scopes that the token
        requires and are assigned to the provider."""

        scopes_from_client = token.scope
        final_claims = {}
        for scope in ScopeMapping.objects.filter(
            provider=token.provider, scope_name__in=scopes_from_client
        ).order_by("scope_name"):
            value = None
            try:
                value = scope.evaluate(
                    user=token.user,
                    request=self.request,
                    provider=token.provider,
                    token=token,
                )
            except PropertyMappingExpressionException as exc:
                Event.new(
                    EventAction.CONFIGURATION_ERROR,
                    message=f"Failed to evaluate property-mapping: {str(exc)}",
                    mapping=scope,
                ).from_http(self.request)
            if value is None:
                continue
            if not isinstance(value, dict):
                LOGGER.warning(
                    "Scope returned a non-dict value, ignoring",
                    scope=scope,
                    value=value,
                )
                continue
            LOGGER.debug("updated scope", scope=scope)
            always_merger.merge(final_claims, value)
        return final_claims

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.token = kwargs.get("token", None)
        response = super().dispatch(request, *args, **kwargs)
        allowed_origins = []
        if self.token:
            allowed_origins = self.token.provider.redirect_uris.split("\n")
        cors_allow(self.request, response, *allowed_origins)
        return response

    def options(self, request: HttpRequest) -> HttpResponse:
        return TokenResponse({})

    def get(self, request: HttpRequest, **kwargs) -> HttpResponse:
        """Handle GET Requests for UserInfo"""
        if not self.token:
            return HttpResponseBadRequest()
        claims = self.get_claims(self.token)
        claims["sub"] = self.token.id_token.sub
        response = TokenResponse(claims)
        return response

    def post(self, request: HttpRequest, **kwargs) -> HttpResponse:
        """POST Requests behave the same as GET Requests, so the get handler is called here"""
        return self.get(request, **kwargs)
