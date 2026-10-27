"""Configuration checks without changing the running Django settings."""
import os
from pathlib import Path
import runpy
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class RenderSettingsTests(SimpleTestCase):
    def load_settings(self, variables):
        with patch.dict(os.environ, variables, clear=True):
            return runpy.run_path(str(Path(__file__).resolve().parents[1] / "config/settings.py"))

    def test_local_development_stays_simple(self):
        settings = self.load_settings({})
        self.assertTrue(settings["DEBUG"])
        self.assertEqual(settings["ALLOWED_HOSTS"], ["localhost", "127.0.0.1"])
        self.assertTrue(str(settings["DATABASES"]["default"]["NAME"]).endswith("local.sqlite3"))
        self.assertNotIn("SECURE_PROXY_SSL_HEADER", settings)

    def test_production_requires_secret(self):
        for variables in ({"DJANGO_DEBUG": "false"}, {"RENDER": "true"}, {"SACRATISSIMUM_PREVIEW": "true"}):
            with self.subTest(variables=variables), self.assertRaises(ImproperlyConfigured):
                self.load_settings(variables)

    def test_render_rejects_debug(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load_settings({"RENDER": "true", "DJANGO_DEBUG": "true"})

    def test_render_host_https_and_static_configuration(self):
        settings = self.load_settings({
            "RENDER": "true", "RENDER_EXTERNAL_HOSTNAME": "assigned-preview.onrender.com",
            "DJANGO_SECRET_KEY": "test-only-never-a-real-secret",
            "SACRATISSIMUM_PREVIEW": "true",
        })
        self.assertFalse(settings["DEBUG"])
        self.assertEqual(settings["ALLOWED_HOSTS"], ["assigned-preview.onrender.com"])
        self.assertEqual(settings["CSRF_TRUSTED_ORIGINS"], ["https://assigned-preview.onrender.com"])
        self.assertEqual(settings["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertTrue(settings["SECURE_SSL_REDIRECT"])
        self.assertTrue(settings["SESSION_COOKIE_SECURE"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])
        self.assertEqual(settings["DATABASES"]["default"]["NAME"], "/tmp/sacratissimum-preview.sqlite3")
        self.assertEqual(settings["MIDDLEWARE"][1], "whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertIn("CompressedManifestStaticFilesStorage", settings["STORAGES"]["staticfiles"]["BACKEND"])

    def test_explicit_host_database_and_origin_overrides_are_preserved(self):
        settings = self.load_settings({
            "RENDER": "true", "RENDER_EXTERNAL_HOSTNAME": "assigned-preview.onrender.com",
            "DJANGO_SECRET_KEY": "test-only-never-a-real-secret",
            "DJANGO_ALLOWED_HOSTS": "extra.example.test, assigned-preview.onrender.com",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://extra.example.test",
            "SACRATISSIMUM_DB_PATH": "/tmp/custom-preview.sqlite3",
        })
        self.assertEqual(settings["ALLOWED_HOSTS"], ["extra.example.test", "assigned-preview.onrender.com"])
        self.assertEqual(settings["DATABASES"]["default"]["NAME"], "/tmp/custom-preview.sqlite3")
        self.assertEqual(len(settings["CSRF_TRUSTED_ORIGINS"]), 2)

    def test_permanent_account_environment_requires_opt_in_and_verified_database_tls(self):
        variables = {
            "DJANGO_DEBUG": "false", "DJANGO_SECRET_KEY": "test-only-not-a-real-secret",
            "DATABASE_URL": "postgresql://test_user:test_password@db.example.test/test_database",
            "EMAIL_HOST": "smtp.example.test", "DEFAULT_FROM_EMAIL": "store@example.test",
            "SITE_URL": "https://store.example.test",
        }
        settings = self.load_settings(variables)
        self.assertFalse(settings["STORE_FEATURES_ENABLED"])
        self.assertEqual(settings["DATABASES"]["default"]["OPTIONS"]["sslmode"], "verify-full")
        self.assertEqual(settings["DATABASES"]["default"]["OPTIONS"]["sslrootcert"], "system")
        settings = self.load_settings({**variables, "ACCOUNTS_ENABLED": "true"})
        self.assertTrue(settings["STORE_FEATURES_ENABLED"])
        with self.assertRaises(ImproperlyConfigured):
            self.load_settings({**variables, "ACCOUNTS_ENABLED": "true", "SACRATISSIMUM_PREVIEW": "true"})
