from django.urls import include, path
from .views import LogoutView, LoginView, RefreshView, UserView
from rest_framework.routers import DefaultRouter

r = DefaultRouter()
r.register("users", UserView, basename="user")

urlpatterns = [
    path("users/login/", LoginView.as_view(), name="login"),
    path("users/refresh/", RefreshView.as_view(), name="refresh"),
    path("users/logout/", LogoutView.as_view(), name="logout"),
    path("", include(r.urls)),
]
