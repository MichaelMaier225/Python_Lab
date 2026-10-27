from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class StoreAdminConfig(AdminConfig):
    default_site = "commerce.admin_site.StoreAdminSite"


class CommerceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "commerce"
