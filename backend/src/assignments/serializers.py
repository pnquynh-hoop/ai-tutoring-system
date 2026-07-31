from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Max
from rest_framework import serializers

from accounts.serializers import SimpleUserSerializer
from assignments.models import Answer, Assignment, Question, StudentAnswer, Submission
from assignments.services import MAX_ATTEMPTS, TOTAL_SCORE, count_submitted_attempts


class QuestionTypeStatSerializer(serializers.Serializer):
    label = serializers.CharField()
    count = serializers.IntegerField()


class AssignmentDetailSerializer(serializers.ModelSerializer):
    total_questions = serializers.IntegerField(read_only=True)
    question_types = serializers.SerializerMethodField()
    max_attempts = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()

    def get_max_attempts(self, obj) -> int:
        return MAX_ATTEMPTS

    def get_attempts_used(self, obj) -> int:
        return count_submitted_attempts(self.context["request"].user, obj)

    def get_question_types(self, obj):
        stats = obj.questions.values("question_type").annotate(count=Count("id"))

        return [
            {
                "label": Question.QuestionType(item["question_type"]).label,
                "count": item["count"],
            }
            for item in stats
        ]

    class Meta:
        model = Assignment
        fields = [
            "id",
            "chapter",
            "title",
            "time_limit_minutes",
            "due_date",
            "total_questions",
            "question_types",
            "max_attempts",
            "attempts_used",
        ]


class AssignmentWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assignment
        fields = ["id", "chapter", "title", "due_date", "time_limit_minutes"]


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "content"]


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "content", "question_type", "answers"]


class AnswerWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Answer
        fields = ["id", "content", "is_correct"]


class QuestionWriteSerializer(serializers.ModelSerializer):
    answers = AnswerWriteSerializer(many=True)
    order = serializers.IntegerField(required=False, allow_null=True, default=None)

    class Meta:
        model = Question
        fields = [
            "id",
            "assignment",
            "content",
            "question_type",
            "explanation",
            "order",
            "answers",
        ]

    def validate(self, attrs):
        question_type = attrs.get(
            "question_type",
            getattr(
                self.instance, "question_type", Question.QuestionType.MULTIPLE_CHOICE
            ),
        )
        answers = attrs.get("answers")

        if answers is None:
            return attrs

        correct_count = sum(1 for answer in answers if answer.get("is_correct"))

        if question_type == Question.QuestionType.MULTIPLE_CHOICE:
            if len(answers) < 2:
                raise serializers.ValidationError(
                    {"answers": "Câu trắc nghiệm cần ít nhất 2 phương án."}
                )
            if correct_count != 1:
                raise serializers.ValidationError(
                    {"answers": "Câu trắc nghiệm phải có đúng 1 phương án đúng."}
                )
        elif question_type == Question.QuestionType.FILL_IN_BLANK:
            if correct_count != 1:
                raise serializers.ValidationError(
                    {"answers": "Câu điền khuyết phải có đúng 1 đáp án đúng."}
                )
        elif answers:
            raise serializers.ValidationError(
                {"answers": "Câu tự luận không cần phương án trả lời."}
            )

        return attrs

    def _next_order(self, assignment):
        current_max = assignment.questions.aggregate(value=Max("order"))["value"] or 0
        return current_max + 1

    @transaction.atomic
    def create(self, validated_data):
        answers = validated_data.pop("answers", [])
        if validated_data.get("order") is None:
            validated_data["order"] = self._next_order(validated_data["assignment"])

        question = Question.objects.create(**validated_data)
        Answer.objects.bulk_create(
            Answer(
                question=question,
                content=answer["content"],
                is_correct=answer["is_correct"],
            )
            for answer in answers
        )
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        answers = validated_data.pop("answers", None)
        if validated_data.get("order") is None:
            validated_data.pop("order", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if answers is not None:
            instance.answers.all().delete()
            Answer.objects.bulk_create(
                Answer(
                    question=instance,
                    content=answer["content"],
                    is_correct=answer["is_correct"],
                )
                for answer in answers
            )
        return instance


class SubmitAnswerItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_id = serializers.IntegerField(required=False, allow_null=True)
    answer_text = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class SubmitAssignmentSerializer(serializers.Serializer):
    answers = SubmitAnswerItemSerializer(many=True)


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    chapter_title = serializers.CharField(
        source="assignment.chapter.title", read_only=True
    )
    course_name = serializers.CharField(
        source="assignment.chapter.course.name", read_only=True
    )
    student = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "chapter_title",
            "course_name",
            "student",
            "score",
            "started_at",
            "submitted_at",
        ]


class AttemptSerializer(serializers.ModelSerializer):
    """Thông tin lượt làm bài đang mở, dùng cho đồng hồ đếm ngược ở client."""

    deadline = serializers.DateTimeField(read_only=True, allow_null=True)
    time_limit_minutes = serializers.IntegerField(
        source="assignment.time_limit_minutes", read_only=True, allow_null=True
    )

    class Meta:
        model = Submission
        fields = ["id", "assignment", "started_at", "deadline", "time_limit_minutes"]


# ----- Xem lại bài làm / chấm bài -----


class StudentAnswerSerializer(serializers.ModelSerializer):
    """Một câu trả lời trong bài nộp, kèm dữ liệu cần cho màn xem lại và chấm bài."""

    question_content = serializers.CharField(source="question.content", read_only=True)
    question_type = serializers.CharField(
        source="question.question_type", read_only=True
    )
    explanation = serializers.CharField(source="question.explanation", read_only=True)
    selected_answer = serializers.CharField(
        source="answer.content", read_only=True, default=None
    )
    correct_answer = serializers.SerializerMethodField()
    is_correct = serializers.SerializerMethodField()

    class Meta:
        model = StudentAnswer
        fields = [
            "id",
            "question",
            "question_content",
            "question_type",
            "explanation",
            "answer",
            "selected_answer",
            "correct_answer",
            "answer_text",
            "point",
            "tutor_comment",
            "is_correct",
        ]

    def get_correct_answer(self, obj) -> str | None:
        correct = next((a for a in obj.question.answers.all() if a.is_correct), None)
        return correct.content if correct else None

    def get_is_correct(self, obj) -> bool | None:
        """None nghĩa là câu tự luận chưa được gia sư chấm."""
        if obj.point is None:
            return None
        return obj.point > 0


class SubmissionDetailSerializer(SubmissionSerializer):
    stu_answers = StudentAnswerSerializer(many=True, read_only=True)
    point_per_question = serializers.SerializerMethodField()

    class Meta(SubmissionSerializer.Meta):
        fields = SubmissionSerializer.Meta.fields + [
            "point_per_question",
            "stu_answers",
        ]

    def get_point_per_question(self, obj) -> float:
        """Điểm tối đa mỗi câu, dùng làm trần khi gia sư chấm tay."""
        total = obj.assignment.questions.count()
        if not total:
            return 0.0
        return float((TOTAL_SCORE / total).quantize(Decimal("0.01")))


class GradeAnswerItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID của StudentAnswer cần chấm")
    point = serializers.DecimalField(
        max_digits=4, decimal_places=2, min_value=Decimal("0")
    )
    tutor_comment = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class GradeSubmissionSerializer(serializers.Serializer):
    answers = GradeAnswerItemSerializer(many=True)
