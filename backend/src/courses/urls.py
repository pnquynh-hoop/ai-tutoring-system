from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CourseView

r = DefaultRouter()
r.register("", CourseView, basename="course")

urlpatterns = [
    path("", include(r.urls))
]

