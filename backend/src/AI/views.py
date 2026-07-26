from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from courses.models import Enrollment, Course
from .rag_service import query_rag_answer, generate_exercises_rag


class RAGAskQuestionView(APIView):
    """API dành cho Học sinh hỏi đáp với AI dựa trên tài liệu bài học"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Hỏi đáp AI theo khóa học / bài học (RAG)",
        description="Trả lời câu hỏi dựa trên ngữ cảnh bài học. Học sinh phải đăng ký khóa học mới có quyền truy cập.",
        request=inline_serializer(
            name="RAGAskRequest",
            fields={
                "question": serializers.CharField(
                    help_text="Nội dung câu hỏi của học sinh"
                ),
                "course_id": serializers.IntegerField(help_text="ID của khóa học"),
                "lesson_id": serializers.IntegerField(
                    required=False, allow_null=True, help_text="ID bài học (nếu có)"
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="RAGAskResponse",
                fields={
                    "question": serializers.CharField(),
                    "answer": serializers.CharField(),
                },
            ),
            403: inline_serializer(
                name="RAGPermissionDenied",
                fields={"error": serializers.CharField()},
            ),
        },
    )
    def post(self, request):
        question = request.data.get("question")
        course_id = request.data.get("course_id")
        lesson_id = request.data.get("lesson_id")

        if not question or not course_id:
            return Response(
                {"error": "Vui lòng cung cấp đầy đủ 'question' và 'course_id'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Kiểm tra Học sinh đã đăng ký khóa học này chưa
        is_enrolled = Enrollment.objects.filter(
            student=request.user, course_id=course_id, is_active=True
        ).exists()

        # Cho phép Tutor của khóa học hoặc Học sinh đã Enroll
        is_course_tutor = Course.objects.filter(
            id=course_id, tutor=request.user
        ).exists()

        if not (is_enrolled or is_course_tutor or request.user.is_staff):
            return Response(
                {"error": "Bạn không có quyền truy cập tài liệu của khóa học này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Gọi hàm RAG
        answer = query_rag_answer(
            query=question, course_id=course_id, lesson_id=lesson_id
        )

        return Response(
            {
                "question": question,
                "answer": answer,
            },
            status=status.HTTP_200_OK,
        )


class RAGGenerateExercisesView(APIView):
    """API dành cho Tutor / Admin tạo bài tập tự động từ tài liệu bài học"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Tạo bộ câu hỏi bài tập tự động bằng AI",
        description="Sinh danh sách câu hỏi trắc nghiệm/tự luận kèm đáp án và lời giải chi tiết dựa trên nội dung bài học.",
        request=inline_serializer(
            name="GenerateExerciseRequest",
            fields={
                "course_id": serializers.IntegerField(),
                "lesson_id": serializers.IntegerField(required=False, allow_null=True),
                "question_type": serializers.ChoiceField(
                    choices=["MULTIPLE_CHOICE", "ESSAY", "FILL_IN_BLANK"],
                    default="MULTIPLE_CHOICE",
                ),
                "count": serializers.IntegerField(default=5, min_value=1, max_value=20),
            },
        ),
        responses={
            200: inline_serializer(
                name="GenerateExerciseResponse",
                fields={
                    "count": serializers.IntegerField(),
                    "questions": serializers.ListField(),
                },
            )
        },
    )
    def post(self, request):
        # Chỉ Tutor hoặc Admin mới có quyền tạo bài tập
        if not (request.user.is_tutor or request.user.is_staff):
            return Response(
                {
                    "error": "Chỉ Trợ giảng / Giảng viên mới có quyền tạo bài tập tự động."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        course_id = request.data.get("course_id")
        lesson_id = request.data.get("lesson_id")
        question_type = request.data.get("question_type", "MULTIPLE_CHOICE")
        count = int(request.data.get("count", 5))

        if not course_id:
            return Response(
                {"error": "Vui lòng cung cấp 'course_id'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            questions = generate_exercises_rag(
                course_id=course_id,
                lesson_id=lesson_id,
                question_type=question_type,
                count=count,
            )
            return Response(
                {
                    "count": len(questions),
                    "questions": questions,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Không thể khởi tạo bài tập: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
