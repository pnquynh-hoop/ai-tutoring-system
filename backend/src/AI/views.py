import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from core.permissions import (
    IsRelatedCourseMember,
    IsRelatedCourseTutor,
    IsStudentOrTutor,
    IsTutor,
)
from courses.models import Course

from .rag_service import generate_exercises_rag, query_rag_answer
from .serializers import (
    GenerateExercisesResponseSerializer,
    GenerateExercisesSerializer,
    RAGAnswerSerializer,
    RAGAskSerializer,
)

logger = logging.getLogger(__name__)

AI_UNAVAILABLE = "Trợ lý AI hiện không phản hồi được, vui lòng thử lại sau."


class RAGAskQuestionView(GenericAPIView):
    """API dành cho Học sinh hỏi đáp với AI dựa trên tài liệu bài học.

    Quyền truy cập khóa học do IsRelatedCourseMember chặn từ trước khi handler chạy,
    view chỉ còn việc kiểm tra dữ liệu đầu vào và gọi service.
    """

    serializer_class = RAGAskSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"
    write_parent_lookup = ("course_id", Course)
    permission_classes = [IsStudentOrTutor, IsRelatedCourseMember]

    @extend_schema(
        summary="Hỏi đáp AI theo khóa học / bài học (RAG)",
        description="Trả lời câu hỏi dựa trên ngữ cảnh bài học. Học sinh phải đăng ký khóa học mới có quyền truy cập.",
        request=RAGAskSerializer,
        responses={200: RAGAnswerSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = query_rag_answer(
                query=data["question"],
                course_id=data["course_id"],
                lesson_id=data.get("lesson_id"),
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
    """API dành cho Tutor phụ trách khóa học tạo bài tập tự động từ tài liệu bài học."""

    serializer_class = GenerateExercisesSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"
    write_parent_lookup = ("course_id", Course)
    permission_classes = [IsTutor, IsRelatedCourseTutor]

    @extend_schema(
        summary="Tạo bộ câu hỏi bài tập tự động bằng AI",
        description="Sinh danh sách câu hỏi kèm đáp án và lời giải chi tiết dựa trên nội dung bài học.",
        request=GenerateExercisesSerializer,
        responses={200: GenerateExercisesResponseSerializer},
    )
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
