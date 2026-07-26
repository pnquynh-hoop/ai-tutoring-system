from django.urls import path
from .views import RAGAskQuestionView, RAGGenerateExercisesView

urlpatterns = [
    path("rag/ask/", RAGAskQuestionView.as_view(), name="rag-ask"),
    path(
        "rag/generate-exercises/",
        RAGGenerateExercisesView.as_view(),
        name="rag-generate-exercises",
    ),
]
