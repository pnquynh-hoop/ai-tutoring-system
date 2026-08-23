"""
URL configuration for ai_tutoring_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from core.admin import admin_site

api_v1_patterns = [
    path("", include("accounts.urls")),
    path("", include("academics.urls")),
    path("", include("courses.urls")),
    path("", include("assignments.urls")),
    path("", include("AI.urls")),
]

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("", RedirectView.as_view(url="/api/docs/", permanent=False)),
    path("admin/", admin_site.urls),
    path("api/v1/", include(api_v1_patterns)),
    path("__debug__/", include("debug_toolbar.urls")),
]
