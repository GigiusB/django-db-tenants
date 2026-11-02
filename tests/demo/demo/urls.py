from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("whoami/", views.whoami, name="whoami"),
    path("healthz", views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("sso/", include("django_db_tenants.sso.urls")),  # per-tenant OIDC login
    path("notes/", include("notes.urls")),
]
