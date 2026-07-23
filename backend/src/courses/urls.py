from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CourseView, LessonView, QuickStatsView

r = DefaultRouter()
r.register("courses", CourseView, basename="course")
r.register("lessons", LessonView, basename="lesson")

urlpatterns = [
    path("statistic/", QuickStatsView.as_view(), name="quick-stats"),
    path("", include(r.urls)),
]

