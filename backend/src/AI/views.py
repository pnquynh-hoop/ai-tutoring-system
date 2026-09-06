import logging
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from core.permissions import IsRelatedCourseMember, IsStudent
from courses.models import Course
from .rag_service import generate_exercises_rag, query_rag_answer
from .serializers import (
    GenerateExercisesSerializer,
    RAGAnswerSerializer,
    RAGAskSerializer,
)

logger = logging.getLogger(__name__)

AI_UNAVAILABLE = "Trợ lý AI hiện không phản hồi được, vui lòng thử lại sau."


class RAGAskQuestionView(GenericAPIView):

    serializer_class = RAGAskSerializer
    throttle_scope = "ai"
    write_parent_lookup = ("course_id", Course)
    permission_classes = [IsStudent, IsRelatedCourseMember]

    def post(self, request):
        serializer = RAGAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = query_rag_answer(
                query=data["question"],
                course_id=data["course_id"],
                lesson_id=data.get("lesson_id"),
                student=request.user,
            )
        except Exception:
            logger.exception("Lỗi khi gọi RAG cho course_id=%s", data["course_id"])
            return Response(
                {"error": AI_UNAVAILABLE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            RAGAnswerSerializer({"question": data["question"], **result}).data,
            status=status.HTTP_200_OK,
        )


class RAGGenerateExercisesView(GenericAPIView):

    serializer_class = GenerateExercisesSerializer
    throttle_scope = "ai"
    write_parent_lookup = ("course_id", Course)
    permission_classes = [IsStudent, IsRelatedCourseMember]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            questions = generate_exercises_rag(
                course_id=data["course_id"],
                lesson_id=data.get("lesson_id"),
                question_type=data["question_type"],
                count=data["count"],
            )
        except Exception:
            logger.exception("Lỗi khi sinh bài tập cho course_id=%s", data["course_id"])
            return Response(
                {"error": AI_UNAVAILABLE},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"count": len(questions), "questions": questions},
            status=status.HTTP_200_OK,
        )
