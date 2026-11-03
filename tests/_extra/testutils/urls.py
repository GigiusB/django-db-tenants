"""The demo project's URLs plus the OIDC login views, which the demo does not use."""

from django.urls import include, path

from demo.urls import urlpatterns as demo_urlpatterns

urlpatterns = [
    *demo_urlpatterns,
    path("oidc/", include("django_db_tenants.oidc.urls")),
]
