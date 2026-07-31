from rest_framework import serializers

from assignments.models import Question


class RAGAskSerializer(serializers.Serializer):
    question = serializers.CharField(help_text="Nội dung câu hỏi của học sinh")
    course_id = serializers.IntegerField(help_text="ID của khóa học")
    lesson_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="ID bài học (nếu có)"
    )


class RAGSourceSerializer(serializers.Serializer):
    """Nguồn tài liệu AI đã dùng để trả lời, hiển thị lại cho học sinh đối chiếu."""

    title = serializers.CharField()
    page = serializers.IntegerField(allow_null=True, required=False)


class RAGAnswerSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField()
    sources = RAGSourceSerializer(many=True)
    # False nghĩa là câu trả lời lấy từ kiến thức chung, không có trong tài liệu.
    grounded = serializers.BooleanField()


class GenerateExercisesSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    lesson_id = serializers.IntegerField(required=False, allow_null=True)
    question_type = serializers.ChoiceField(
        choices=Question.QuestionType.choices,
        default=Question.QuestionType.MULTIPLE_CHOICE,
    )
    count = serializers.IntegerField(default=5, min_value=1, max_value=20)


class GeneratedAnswerSerializer(serializers.Serializer):
    content = serializers.CharField()
    is_correct = serializers.BooleanField()


class GeneratedQuestionSerializer(serializers.Serializer):
    content = serializers.CharField()
    explanation = serializers.CharField()
    answers = GeneratedAnswerSerializer(many=True)


class GenerateExercisesResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    questions = GeneratedQuestionSerializer(many=True)
