"""LDAP and Outpost e2e tests"""
from sys import platform
from time import sleep
from unittest.case import skipUnless

from docker.client import DockerClient, from_env
from docker.models.containers import Container
from guardian.shortcuts import get_anonymous_user
from ldap3 import ALL, ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPInvalidCredentialsResult

from authentik.core.models import Application, Group, User
from authentik.events.models import Event, EventAction
from authentik.flows.models import Flow
from authentik.outposts.managed import MANAGED_OUTPOST
from authentik.outposts.models import Outpost, OutpostType
from authentik.providers.ldap.models import LDAPProvider
from tests.e2e.utils import (
    USER,
    SeleniumTestCase,
    apply_migration,
    get_docker_tag,
    object_manager,
    retry,
)


@skipUnless(platform.startswith("linux"), "requires local docker")
class TestProviderLDAP(SeleniumTestCase):
    """LDAP and Outpost e2e tests"""

    ldap_container: Container

    def tearDown(self) -> None:
        super().tearDown()
        self.output_container_logs(self.ldap_container)
        self.ldap_container.kill()

    def start_ldap(self, outpost: Outpost) -> Container:
        """Start ldap container based on outpost created"""
        client: DockerClient = from_env()
        container = client.containers.run(
            image=f"beryju.org/authentik/outpost-ldap:{get_docker_tag()}",
            detach=True,
            network_mode="host",
            auto_remove=True,
            environment={
                "AUTHENTIK_HOST": self.live_server_url,
                "AUTHENTIK_TOKEN": outpost.token.key,
            },
        )
        return container

    def _prepare(self) -> User:
        """prepare user, provider, app and container"""
        # set additionalHeaders to test later
        user = USER()
        user.attributes["extraAttribute"] = "bar"
        user.save()

        ldap: LDAPProvider = LDAPProvider.objects.create(
            name="ldap_provider",
            authorization_flow=Flow.objects.get(slug="default-authentication-flow"),
            search_group=Group.objects.first(),
        )
        # we need to create an application to actually access the ldap
        Application.objects.create(name="ldap", slug="ldap", provider=ldap)
        outpost: Outpost = Outpost.objects.create(
            name="ldap_outpost",
            type=OutpostType.LDAP,
        )
        outpost.providers.add(ldap)
        outpost.save()
        user = outpost.user

        self.ldap_container = self.start_ldap(outpost)

        # Wait until outpost healthcheck succeeds
        healthcheck_retries = 0
        while healthcheck_retries < 50:
            if len(outpost.state) > 0:
                state = outpost.state[0]
                if state.last_seen:
                    break
            healthcheck_retries += 1
            sleep(0.5)
        return user

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_flows", "0008_default_flows")
    @object_manager
    def test_ldap_bind_success(self):
        """Test simple bind"""
        self._prepare()
        server = Server("ldap://localhost:3389", get_info=ALL)
        _connection = Connection(
            server,
            raise_exceptions=True,
            user=f"cn={USER().username},ou=users,DC=ldap,DC=goauthentik,DC=io",
            password=USER().username,
        )
        _connection.bind()
        self.assertTrue(
            Event.objects.filter(
                action=EventAction.LOGIN,
                user={
                    "pk": USER().pk,
                    "email": USER().email,
                    "username": USER().username,
                },
            )
        )

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_flows", "0008_default_flows")
    @object_manager
    def test_ldap_bind_success_ssl(self):
        """Test simple bind with ssl"""
        self._prepare()
        server = Server("ldaps://localhost:6636", get_info=ALL)
        _connection = Connection(
            server,
            raise_exceptions=True,
            user=f"cn={USER().username},ou=users,DC=ldap,DC=goauthentik,DC=io",
            password=USER().username,
        )
        _connection.bind()
        self.assertTrue(
            Event.objects.filter(
                action=EventAction.LOGIN,
                user={
                    "pk": USER().pk,
                    "email": USER().email,
                    "username": USER().username,
                },
            )
        )

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_flows", "0008_default_flows")
    @object_manager
    def test_ldap_bind_fail(self):
        """Test simple bind (failed)"""
        self._prepare()
        server = Server("ldap://localhost:3389", get_info=ALL)
        _connection = Connection(
            server,
            raise_exceptions=True,
            user=f"cn={USER().username},ou=users,DC=ldap,DC=goauthentik,DC=io",
            password=USER().username + "fqwerwqer",
        )
        with self.assertRaises(LDAPInvalidCredentialsResult):
            _connection.bind()
        anon = get_anonymous_user()
        self.assertTrue(
            Event.objects.filter(
                action=EventAction.LOGIN_FAILED,
                user={"pk": anon.pk, "email": anon.email, "username": anon.username},
            )
        )

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_core", "0009_group_is_superuser")
    @apply_migration("authentik_flows", "0008_default_flows")
    @object_manager
    def test_ldap_bind_search(self):
        """Test simple bind + search"""
        outpost_user = self._prepare()
        server = Server("ldap://localhost:3389", get_info=ALL)
        _connection = Connection(
            server,
            raise_exceptions=True,
            user=f"cn={USER().username},ou=users,dc=ldap,dc=goauthentik,dc=io",
            password=USER().username,
        )
        _connection.bind()
        self.assertTrue(
            Event.objects.filter(
                action=EventAction.LOGIN,
                user={
                    "pk": USER().pk,
                    "email": USER().email,
                    "username": USER().username,
                },
            )
        )

        embedded_account = Outpost.objects.filter(managed=MANAGED_OUTPOST).first().user

        _connection.search(
            "ou=users,dc=ldap,dc=goauthentik,dc=io",
            "(objectClass=user)",
            search_scope=SUBTREE,
            attributes=[ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES],
        )
        response = _connection.response
        # Remove raw_attributes to make checking easier
        for obj in response:
            del obj["raw_attributes"]
            del obj["raw_dn"]
        self.assertCountEqual(
            response,
            [
                {
                    "dn": f"cn={outpost_user.username},ou=users,dc=ldap,dc=goauthentik,dc=io",
                    "attributes": {
                        "cn": [outpost_user.username],
                        "sAMAccountName": [outpost_user.username],
                        "uid": [outpost_user.uid],
                        "name": [""],
                        "displayName": [""],
                        "mail": [""],
                        "objectClass": [
                            "user",
                            "organizationalPerson",
                            "goauthentik.io/ldap/user",
                        ],
                        "uidNumber": [str(2000 + outpost_user.pk)],
                        "gidNumber": [str(2000 + outpost_user.pk)],
                        "memberOf": [],
                        "accountStatus": ["true"],
                        "superuser": ["false"],
                        "goauthentik.io/ldap/active": ["true"],
                        "goauthentik.io/ldap/superuser": ["false"],
                        "goauthentik.io/user/override-ips": ["true"],
                        "goauthentik.io/user/service-account": ["true"],
                    },
                    "type": "searchResEntry",
                },
                {
                    "dn": f"cn={embedded_account.username},ou=users,dc=ldap,dc=goauthentik,dc=io",
                    "attributes": {
                        "cn": [embedded_account.username],
                        "sAMAccountName": [embedded_account.username],
                        "uid": [embedded_account.uid],
                        "name": [""],
                        "displayName": [""],
                        "mail": [""],
                        "objectClass": [
                            "user",
                            "organizationalPerson",
                            "goauthentik.io/ldap/user",
                        ],
                        "uidNumber": [str(2000 + embedded_account.pk)],
                        "gidNumber": [str(2000 + embedded_account.pk)],
                        "memberOf": [],
                        "accountStatus": ["true"],
                        "superuser": ["false"],
                        "goauthentik.io/ldap/active": ["true"],
                        "goauthentik.io/ldap/superuser": ["false"],
                        "goauthentik.io/user/override-ips": ["true"],
                        "goauthentik.io/user/service-account": ["true"],
                    },
                    "type": "searchResEntry",
                },
                {
                    "dn": f"cn={USER().username},ou=users,dc=ldap,dc=goauthentik,dc=io",
                    "attributes": {
                        "cn": [USER().username],
                        "sAMAccountName": [USER().username],
                        "uid": [USER().uid],
                        "name": [USER().name],
                        "displayName": [USER().name],
                        "mail": [USER().email],
                        "objectClass": [
                            "user",
                            "organizationalPerson",
                            "goauthentik.io/ldap/user",
                        ],
                        "uidNumber": [str(2000 + USER().pk)],
                        "gidNumber": [str(2000 + USER().pk)],
                        "memberOf": ["cn=authentik Admins,ou=groups,dc=ldap,dc=goauthentik,dc=io"],
                        "accountStatus": ["true"],
                        "superuser": ["true"],
                        "goauthentik.io/ldap/active": ["true"],
                        "goauthentik.io/ldap/superuser": ["true"],
                        "extraAttribute": ["bar"],
                    },
                    "type": "searchResEntry",
                },
            ],
        )
