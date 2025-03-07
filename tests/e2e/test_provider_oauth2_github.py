"""test OAuth Provider flow"""
from sys import platform
from time import sleep
from typing import Any, Optional
from unittest.case import skipUnless

from docker.types import Healthcheck
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

from authentik.core.models import Application
from authentik.flows.models import Flow
from authentik.lib.generators import generate_id, generate_key
from authentik.policies.expression.models import ExpressionPolicy
from authentik.policies.models import PolicyBinding
from authentik.providers.oauth2.models import ClientTypes, OAuth2Provider
from tests.e2e.utils import USER, SeleniumTestCase, apply_migration, retry


@skipUnless(platform.startswith("linux"), "requires local docker")
class TestProviderOAuth2Github(SeleniumTestCase):
    """test OAuth Provider flow"""

    def setUp(self):
        self.client_id = generate_id()
        self.client_secret = generate_key()
        super().setUp()

    def get_container_specs(self) -> Optional[dict[str, Any]]:
        """Setup client grafana container which we test OAuth against"""
        return {
            "image": "grafana/grafana:7.1.0",
            "detach": True,
            "network_mode": "host",
            "auto_remove": True,
            "healthcheck": Healthcheck(
                test=["CMD", "wget", "--spider", "http://localhost:3000"],
                interval=5 * 100 * 1000000,
                start_period=1 * 100 * 1000000,
            ),
            "environment": {
                "GF_AUTH_GITHUB_ENABLED": "true",
                "GF_AUTH_GITHUB_ALLOW_SIGN_UP": "true",
                "GF_AUTH_GITHUB_CLIENT_ID": self.client_id,
                "GF_AUTH_GITHUB_CLIENT_SECRET": self.client_secret,
                "GF_AUTH_GITHUB_SCOPES": "user:email,read:org",
                "GF_AUTH_GITHUB_AUTH_URL": self.url(
                    "authentik_providers_oauth2_github:github-authorize"
                ),
                "GF_AUTH_GITHUB_TOKEN_URL": self.url(
                    "authentik_providers_oauth2_github:github-access-token"
                ),
                "GF_AUTH_GITHUB_API_URL": self.url("authentik_providers_oauth2_github:github-user"),
                "GF_LOG_LEVEL": "debug",
            },
        }

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_flows", "0008_default_flows")
    @apply_migration("authentik_flows", "0011_flow_title")
    @apply_migration("authentik_flows", "0010_provider_flows")
    @apply_migration("authentik_crypto", "0002_create_self_signed_kp")
    def test_authorization_consent_implied(self):
        """test OAuth Provider flow (default authorization flow with implied consent)"""
        # Bootstrap all needed objects
        authorization_flow = Flow.objects.get(
            slug="default-provider-authorization-implicit-consent"
        )
        provider = OAuth2Provider.objects.create(
            name="grafana",
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_type=ClientTypes.CONFIDENTIAL,
            redirect_uris="http://localhost:3000/login/github",
            authorization_flow=authorization_flow,
        )
        Application.objects.create(
            name="Grafana",
            slug="grafana",
            provider=provider,
        )

        self.driver.get("http://localhost:3000")
        self.driver.find_element(By.CLASS_NAME, "btn-service--github").click()
        self.login()

        self.wait_for_url("http://localhost:3000/?orgId=1")
        self.driver.get("http://localhost:3000/profile")
        self.assertEqual(
            self.driver.find_element(By.CLASS_NAME, "page-header__title").text,
            USER().username,
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "input[name=name]").get_attribute("value"),
            USER().username,
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "input[name=email]").get_attribute("value"),
            USER().email,
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "input[name=login]").get_attribute("value"),
            USER().username,
        )

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_flows", "0008_default_flows")
    @apply_migration("authentik_flows", "0011_flow_title")
    @apply_migration("authentik_flows", "0010_provider_flows")
    @apply_migration("authentik_crypto", "0002_create_self_signed_kp")
    def test_authorization_consent_explicit(self):
        """test OAuth Provider flow (default authorization flow with explicit consent)"""
        # Bootstrap all needed objects
        authorization_flow = Flow.objects.get(
            slug="default-provider-authorization-explicit-consent"
        )
        provider = OAuth2Provider.objects.create(
            name="grafana",
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_type=ClientTypes.CONFIDENTIAL,
            redirect_uris="http://localhost:3000/login/github",
            authorization_flow=authorization_flow,
        )
        app = Application.objects.create(
            name="Grafana",
            slug="grafana",
            provider=provider,
        )

        self.driver.get("http://localhost:3000")
        self.driver.find_element(By.CLASS_NAME, "btn-service--github").click()
        self.login()

        sleep(3)
        self.wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "ak-flow-executor")))

        flow_executor = self.get_shadow_root("ak-flow-executor")
        consent_stage = self.get_shadow_root("ak-stage-consent", flow_executor)

        self.assertIn(
            app.name,
            consent_stage.find_element(By.CSS_SELECTOR, "#header-text").text,
        )
        self.assertEqual(
            "GitHub Compatibility: Access you Email addresses",
            consent_stage.find_element(By.CSS_SELECTOR, "[data-permission-code='user:email']").text,
        )
        consent_stage.find_element(
            By.CSS_SELECTOR,
            ("[type=submit]"),
        ).click()

        self.wait_for_url("http://localhost:3000/?orgId=1")
        self.driver.get("http://localhost:3000/profile")
        self.assertEqual(
            self.driver.find_element(By.CLASS_NAME, "page-header__title").text,
            USER().username,
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "input[name=name]").get_attribute("value"),
            USER().username,
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "input[name=email]").get_attribute("value"),
            USER().email,
        )
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "input[name=login]").get_attribute("value"),
            USER().username,
        )

    @retry()
    @apply_migration("authentik_core", "0003_default_user")
    @apply_migration("authentik_flows", "0008_default_flows")
    @apply_migration("authentik_flows", "0011_flow_title")
    @apply_migration("authentik_flows", "0010_provider_flows")
    @apply_migration("authentik_crypto", "0002_create_self_signed_kp")
    def test_denied(self):
        """test OAuth Provider flow (default authorization flow, denied)"""
        # Bootstrap all needed objects
        authorization_flow = Flow.objects.get(
            slug="default-provider-authorization-explicit-consent"
        )
        provider = OAuth2Provider.objects.create(
            name="grafana",
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_type=ClientTypes.CONFIDENTIAL,
            redirect_uris="http://localhost:3000/login/github",
            authorization_flow=authorization_flow,
        )
        app = Application.objects.create(
            name="Grafana",
            slug="grafana",
            provider=provider,
        )

        negative_policy = ExpressionPolicy.objects.create(
            name="negative-static", expression="return False"
        )
        PolicyBinding.objects.create(target=app, policy=negative_policy, order=0)

        self.driver.get("http://localhost:3000")
        self.driver.find_element(By.CLASS_NAME, "btn-service--github").click()
        self.login()

        self.wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "header > h1")))
        self.assertEqual(
            self.driver.find_element(By.CSS_SELECTOR, "header > h1").text,
            "Permission denied",
        )
