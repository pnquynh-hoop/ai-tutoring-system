from django.urls import include, path
from rest_framework.routers import DefaultRouter

from assignments.views import AssignmentView, QuestionView, SubmissionView

r = DefaultRouter()
r.register("assignments", AssignmentView, basename="assignment")
r.register("questions", QuestionView, basename="question")
r.register("submissions", SubmissionView, basename="submission")

urlpatterns = [
    path("", include(r.urls)),
]
