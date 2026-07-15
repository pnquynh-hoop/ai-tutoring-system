from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from .views import LogoutView

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="providing_token"),
    path("refresh/", TokenRefreshView.as_view(), name="refreshing_token"),
    # path("logout/", LogoutView.as_view(), name="logout"),
]
