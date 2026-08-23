from rest_framework import serializers
from assignments.models import Question


MAX_QUESTION_LENGTH = 1000


class RAGAskSerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=MAX_QUESTION_LENGTH, help_text="Nội dung câu hỏi của học sinh"
    )
    course_id = serializers.IntegerField(help_text="ID của khóa học")
    lesson_id = serializers.IntegerField(
        required=False, allow_null=True, help_text="ID bài học (nếu có)"
    )


class RAGSourceSerializer(serializers.Serializer):
    title = serializers.CharField()
    page = serializers.IntegerField(allow_null=True, required=False)


class RAGAnswerSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField()
    sources = RAGSourceSerializer(many=True)
    grounded = serializers.BooleanField()


class GenerateExercisesSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    lesson_id = serializers.IntegerField(required=False, allow_null=True)
    question_type = serializers.ChoiceField(
        choices=Question.QuestionType.choices,
        default=Question.QuestionType.MULTIPLE_CHOICE,
    )
    count = serializers.IntegerField(default=5, min_value=1, max_value=20)
