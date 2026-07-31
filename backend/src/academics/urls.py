from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import GradeView

r = DefaultRouter()
r.register("grades", GradeView, basename="grade")

urlpatterns = [
    path("", include(r.urls)),
]
