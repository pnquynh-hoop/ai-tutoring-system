from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import SimpleUserSerializer
from assignments.models import Answer, Assignment, Question, StudentAnswer, Submission
from assignments.services import (
    MAX_ATTEMPTS,
    count_submitted_attempts,
    has_submissions,
    point_per_question,
)

MAX_TIME_LIMIT_MINUTES = 1440
MAX_ANSWERS_PER_QUESTION = 10
MAX_ANSWER_LENGTH = 1000
MAX_QUESTION_LENGTH = 5000
MAX_ANSWER_TEXT_LENGTH = 10000
MAX_TUTOR_COMMENT_LENGTH = 2000
MAX_ITEMS_PER_REQUEST = 200


class AssignmentDetailSerializer(serializers.ModelSerializer):
    total_questions = serializers.IntegerField(read_only=True)
    question_types = serializers.SerializerMethodField()
    max_attempts = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()
    is_published = serializers.BooleanField(read_only=True)

    def get_max_attempts(self, obj):
        return MAX_ATTEMPTS

    def get_attempts_used(self, obj):
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
            "title",
            "time_limit_minutes",
            "due_date",
            "total_questions",
            "question_types",
            "max_attempts",
            "attempts_used",
            "is_published",
        ]


class AssignmentWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assignment
        fields = ["id", "chapter", "title", "due_date", "time_limit_minutes"]
        extra_kwargs = {
            "time_limit_minutes": {
                "min_value": 1,
                "max_value": MAX_TIME_LIMIT_MINUTES,
            },
        }

    def validate_due_date(self, due_date):
        if due_date <= timezone.now():
            raise serializers.ValidationError(
                "Hạn nộp phải sau thời điểm hiện tại."
            )
        return due_date


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
        extra_kwargs = {"content": {"max_length": MAX_ANSWER_LENGTH}}


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
        extra_kwargs = {
            "content": {"max_length": MAX_QUESTION_LENGTH},
            "explanation": {"max_length": MAX_QUESTION_LENGTH},
        }

    def validate_answers(self, answers):
        if len(answers) > MAX_ANSWERS_PER_QUESTION:
            raise serializers.ValidationError(
                f"Mỗi câu hỏi chỉ có tối đa {MAX_ANSWERS_PER_QUESTION} phương án."
            )
        return answers

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

        if self.instance and has_submissions(self.instance.assignment):
            raise serializers.ValidationError(
                {"answers": "Bài tập đã có bài nộp nên không sửa được phương án."}
            )

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
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=MAX_ANSWER_TEXT_LENGTH,
    )


def validate_item_count(items):
    if len(items) > MAX_ITEMS_PER_REQUEST:
        raise serializers.ValidationError(
            f"Mỗi lần gửi tối đa {MAX_ITEMS_PER_REQUEST} câu."
        )
    return items


class SubmitAssignmentSerializer(serializers.Serializer):
    answers = SubmitAnswerItemSerializer(many=True)

    def validate_answers(self, answers):
        return validate_item_count(answers)


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    chapter_title = serializers.CharField(
        source="assignment.chapter.title", read_only=True
    )
    course_name = serializers.CharField(
        source="assignment.chapter.course.name", read_only=True
    )

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "chapter_title",
            "course_name",
            "score",
            "started_at",
            "submitted_at",
        ]


class TutorSubmissionSerializer(SubmissionSerializer):
    student = SimpleUserSerializer(read_only=True)

    class Meta(SubmissionSerializer.Meta):
        fields = SubmissionSerializer.Meta.fields + ["student"]


class AttemptSerializer(serializers.ModelSerializer):
    deadline = serializers.DateTimeField(read_only=True, allow_null=True)
    time_limit_minutes = serializers.IntegerField(
        source="assignment.time_limit_minutes", read_only=True, allow_null=True
    )

    class Meta:
        model = Submission
        fields = ["id", "assignment", "started_at", "deadline", "time_limit_minutes"]


class StudentAnswerSerializer(serializers.ModelSerializer):
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

    def get_correct_answer(self, obj):
        correct = next((a for a in obj.question.answers.all() if a.is_correct), None)
        return correct.content if correct else None

    def get_is_correct(self, obj):
        if obj.point is None:
            return None
        return obj.point > 0

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


class SubmissionDetailSerializer(SubmissionSerializer):
    stu_answers = StudentAnswerSerializer(many=True, read_only=True)
    point_per_question = serializers.SerializerMethodField()

    def get_point_per_question(self, obj):
        return float(point_per_question(obj.assignment.questions.count()))

    class Meta(SubmissionSerializer.Meta):
        fields = SubmissionSerializer.Meta.fields + [
            "point_per_question",
            "stu_answers",
        ]


class TutorSubmissionDetailSerializer(SubmissionDetailSerializer):
    student = SimpleUserSerializer(read_only=True)

    class Meta(SubmissionDetailSerializer.Meta):
        fields = SubmissionDetailSerializer.Meta.fields + ["student"]


class GradeAnswerItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID của StudentAnswer cần chấm")
    point = serializers.DecimalField(
        max_digits=4, decimal_places=2, min_value=Decimal("0")
    )
    tutor_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=MAX_TUTOR_COMMENT_LENGTH,
    )


class GradeSubmissionSerializer(serializers.Serializer):
    answers = GradeAnswerItemSerializer(many=True)

    def validate_answers(self, answers):
        return validate_item_count(answers)


class PublishAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "published_at"]
        extra_kwargs = {"published_at": {"read_only": True}}

    def validate(self, attrs):
        assignment = self.instance
        chapter = assignment.chapter

        if assignment.is_published:
            raise serializers.ValidationError("Bài tập này đã được công khai.")

        if not chapter.is_published:
            raise serializers.ValidationError(
                "Phải công khai chương chứa bài tập này trước."
            )

        return attrs

    def update(self, instance, validated_data):
        instance.published_at = timezone.now()
        instance.save(update_fields=["published_at", "updated_at"])
        return instance
