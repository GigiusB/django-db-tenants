from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("whoami/", views.whoami, name="whoami"),
    path("healthz", views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("notes/", include("notes.urls")),
]
