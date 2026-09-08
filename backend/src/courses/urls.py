from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    ChapterView,
    CommentView,
    CourseView,
    LessonView,
    QuickStatsView,
    ResourceView,
)

r = DefaultRouter()
r.register("courses", CourseView, basename="course")
r.register("chapters", ChapterView, basename="chapter")
r.register("lessons", LessonView, basename="lesson")
r.register("resources", ResourceView, basename="resource")
r.register("comments", CommentView, basename="comment")

urlpatterns = [
    path("courses/statistic/", QuickStatsView.as_view(), name="quick-stats"),
    path("", include(r.urls)),
]
