# ruff: noqa: F403, F405
from taiga.urls import *

urlpatterns += [
    url(r"^oidc/", include("mozilla_django_oidc.urls")),
]
