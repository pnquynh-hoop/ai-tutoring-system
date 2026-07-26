from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CommentView, CourseView, LessonView, QuickStatsView

r = DefaultRouter()
r.register("courses", CourseView, basename="course")
r.register("lessons", LessonView, basename="lesson")
r.register("comments", CommentView, basename="comment")

urlpatterns = [
    path("statistic/", QuickStatsView.as_view(), name="quick-stats"),
    path("", include(r.urls)),
]

