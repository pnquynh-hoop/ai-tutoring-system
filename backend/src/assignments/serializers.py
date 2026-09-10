from decimal import Decimal
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from rest_framework import serializers
from accounts.serializers import SimpleUserSerializer
from assignments.models import Answer, Assignment, Question, StudentAnswer, Submission
from assignments.services import (
    MAX_ATTEMPTS,
    MIN_QUESTION_POINT,
    POINT_STEP,
    TOTAL_SCORE,
    count_questions_without_point,
    count_used_attempts,
    get_open_attempt,
    has_submissions,
    is_expired,
    is_valid_point_step,
    total_question_points,
)

MAX_TIME_LIMIT_MINUTES = 1440
MAX_ANSWERS_PER_QUESTION = 4
MAX_QUESTIONS_PER_ASSIGNMENT = 100
MAX_ANSWER_LENGTH = 1000
MAX_QUESTION_LENGTH = 5000
MAX_ANSWER_TEXT_LENGTH = 10000
MAX_TUTOR_COMMENT_LENGTH = 2000


class AssignmentDetailSerializer(serializers.ModelSerializer):
    total_questions = serializers.IntegerField(read_only=True)
    question_types = serializers.SerializerMethodField()
    max_attempts = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()
    is_published = serializers.BooleanField(read_only=True)

    def get_max_attempts(self, obj):
        return MAX_ATTEMPTS

    def get_attempts_used(self, obj):
        return count_used_attempts(self.context["request"].user, obj)

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
            raise serializers.ValidationError("Hạn nộp phải sau thời điểm hiện tại.")
        return due_date

    def validate_chapter(self, chapter):
        if chapter.course.tutor_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Bạn không phụ trách khóa học của chương này."
            )
        return chapter

    def validate(self, attrs):
        if self.instance and self.instance.is_published:
            raise serializers.ValidationError(
                "Bài tập đã công khai nên không sửa được nữa."
            )

        if (
            self.instance
            and "chapter" in attrs
            and attrs["chapter"] != self.instance.chapter
        ):
            raise serializers.ValidationError(
                {"chapter": "Không được chuyển bài tập sang chương khác."}
            )
        return attrs


class DeleteAssignmentSerializer(serializers.Serializer):
    def validate(self, attrs):
        assignment = self.instance

        if assignment.is_published:
            raise serializers.ValidationError(
                "Bài tập đã công khai nên không xóa được."
            )

        if has_submissions(assignment):
            raise serializers.ValidationError(
                "Bài tập đã có bài nộp nên không xóa được."
            )
        return attrs


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "content"]


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "content", "question_type", "point", "answers"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.question_type != Question.QuestionType.MULTIPLE_CHOICE:
            data["answers"] = []
        return data


class AnswerWriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Answer
        fields = ["id", "content", "is_correct"]
        extra_kwargs = {"content": {"max_length": MAX_ANSWER_LENGTH}}


class QuestionWriteSerializer(serializers.ModelSerializer):
    answers = AnswerWriteSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "assignment",
            "content",
            "question_type",
            "explanation",
            "point",
            "order",
            "answers",
        ]
        extra_kwargs = {
            "content": {"max_length": MAX_QUESTION_LENGTH},
            "explanation": {"max_length": MAX_QUESTION_LENGTH},
            "point": {
                "required": False,
                "allow_null": True,
                "min_value": MIN_QUESTION_POINT,
                "max_value": TOTAL_SCORE,
            },
        }

    def validate_answers(self, answers):
        if len(answers) > MAX_ANSWERS_PER_QUESTION:
            raise serializers.ValidationError(
                f"Mỗi câu hỏi chỉ có tối đa {MAX_ANSWERS_PER_QUESTION} phương án."
            )
        return answers

    def validate_point(self, point):
        if point is not None and not is_valid_point_step(point):
            raise serializers.ValidationError(
                f"Điểm mỗi câu phải là bội của {POINT_STEP}, ví dụ 0.25, 0.5, 1.75."
            )
        return point

    def validate_assignment(self, assignment):
        if assignment.chapter.course.tutor_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Bạn không phụ trách khóa học của bài tập này."
            )
        return assignment

    def validate(self, attrs):
        if self.instance is None:
            assignment = attrs["assignment"]
            answers = attrs["answers"]
            question_type = attrs.get(
                "question_type", Question.QuestionType.MULTIPLE_CHOICE
            )

            current_count = assignment.questions.count()
            if current_count >= MAX_QUESTIONS_PER_ASSIGNMENT:
                raise serializers.ValidationError(
                    {
                        "assignment": f"Bài tập chỉ có tối đa {MAX_QUESTIONS_PER_ASSIGNMENT} câu hỏi."
                    }
                )
        else:
            assignment = self.instance.assignment
            question_type = attrs.get("question_type", self.instance.question_type)

            if "assignment" in attrs and attrs["assignment"] != assignment:
                raise serializers.ValidationError(
                    {"assignment": "Không được chuyển câu hỏi sang bài tập khác."}
                )

            answers = attrs.get("answers")
            if answers is None:
                answers = []
                for answer in self.instance.answers.all():
                    answers.append(
                        {"content": answer.content, "is_correct": answer.is_correct}
                    )

        if assignment.is_published:
            raise serializers.ValidationError(
                {"assignment": "Bài tập đã công khai nên không thêm hay sửa được câu hỏi."}
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
            if len(answers) != 1:
                raise serializers.ValidationError(
                    {"answers": "Câu điền khuyết chỉ có đúng 1 đáp án."}
                )
            if correct_count != 1:
                raise serializers.ValidationError(
                    {"answers": "Câu điền khuyết phải có đúng 1 đáp án đúng."}
                )
        elif answers:
            raise serializers.ValidationError(
                {"answers": "Câu tự luận không cần phương án trả lời."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        answers = validated_data.pop("answers", [])

        if validated_data.get("order") is None:
            assignment = validated_data["assignment"]
            current_max = (
                assignment.questions.aggregate(value=Max("order"))["value"] or 0
            )
            validated_data["order"] = current_max + 1

        question = Question.objects.create(**validated_data)
        Answer.objects.bulk_create(
            Answer(
                question=question,
                content=answer["content"],
                is_correct=answer.get("is_correct", False),
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
                    is_correct=answer.get("is_correct", False),
                )
                for answer in answers
            )
        return instance


class DeleteQuestionSerializer(serializers.Serializer):
    def validate(self, attrs):
        assignment = self.instance.assignment
        if assignment.is_published:
            raise serializers.ValidationError(
                "Bài tập đã công khai nên không xóa được câu hỏi."
            )
        if has_submissions(assignment):
            raise serializers.ValidationError(
                "Bài tập đã có bài nộp nên không xóa được câu hỏi."
            )
        return attrs


class SubmitAnswerItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_id = serializers.IntegerField(required=False, allow_null=True)
    answer_text = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=MAX_ANSWER_TEXT_LENGTH,
    )


class SubmitAssignmentSerializer(serializers.Serializer):
    answers = SubmitAnswerItemSerializer(many=True)

    def validate(self, attrs):
        assignment = self.instance
        student = self.context["request"].user

        if assignment.due_date and timezone.now() > assignment.due_date:
            raise serializers.ValidationError("Bài tập đã hết hạn nộp.")

        questions = {}
        for question in assignment.questions.all():
            questions[question.id] = question

        attempt = get_open_attempt(student, assignment)

        if attempt is None:
            raise serializers.ValidationError(
                "Bạn chưa bắt đầu lượt làm bài nào cho bài tập này."
            )

        if is_expired(attempt):
            raise serializers.ValidationError(
                "Đã hết thời gian làm bài của lượt làm này."
            )

        answers = attrs["answers"]
        question_ids = [item["question_id"] for item in answers]

        unknown_ids = [
            question_id for question_id in question_ids if question_id not in questions
        ]
        if unknown_ids:
            raise serializers.ValidationError(
                {"answers": f"Các câu hỏi {unknown_ids} không thuộc bài tập này."}
            )

        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError(
                {"answers": "Mỗi câu hỏi chỉ được trả lời một lần."}
            )

        for item in answers:
            answer_id = item.get("answer_id")
            question = questions[item["question_id"]]

            if (
                answer_id is None
                or question.question_type != Question.QuestionType.MULTIPLE_CHOICE
            ):
                continue

            if not any(a.id == answer_id for a in question.answers.all()):
                raise serializers.ValidationError(
                    {
                        "answers": f"Phương án {answer_id} không thuộc câu hỏi {question.id}."
                    }
                )
        return attrs


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

    class Meta:
        model = SubmissionSerializer.Meta.model
        fields = SubmissionSerializer.Meta.fields + ["student"]


class StartAttemptSerializer(serializers.Serializer):
    def validate(self, attrs):
        assignment = self.instance
        student = self.context["request"].user

        if timezone.now() > assignment.due_date:
            raise serializers.ValidationError("Bài tập đã hết hạn nộp.")

        open_attempt = get_open_attempt(student, assignment)
        attrs["open_attempt"] = open_attempt

        if open_attempt is not None and not is_expired(open_attempt):
            return attrs

        used_attempts = count_used_attempts(student, assignment)

        if used_attempts >= MAX_ATTEMPTS:
            raise serializers.ValidationError(
                f"Bạn đã dùng hết {MAX_ATTEMPTS} lượt làm bài của bài tập này."
            )
        return attrs


class AttemptSerializer(serializers.ModelSerializer):
    deadline = serializers.DateTimeField(read_only=True, allow_null=True)
    time_limit_minutes = serializers.IntegerField(
        source="assignment.time_limit_minutes", read_only=True, allow_null=True
    )
    server_time = serializers.SerializerMethodField()

    def get_server_time(self, attempt):
        return timezone.localtime().isoformat()

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment",
            "started_at",
            "deadline",
            "time_limit_minutes",
            "server_time",
        ]


class StudentAnswerSerializer(serializers.ModelSerializer):
    question_content = serializers.CharField(source="question.content", read_only=True)
    question_type = serializers.CharField(
        source="question.question_type", read_only=True
    )
    explanation = serializers.CharField(source="question.explanation", read_only=True)
    question_point = serializers.DecimalField(
        source="question.point", max_digits=4, decimal_places=2, read_only=True
    )
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
            "question_point",
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

    class Meta(SubmissionSerializer.Meta):
        fields = SubmissionSerializer.Meta.fields + ["stu_answers"]


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

    def validate_point(self, point):
        if not is_valid_point_step(point):
            raise serializers.ValidationError(
                f"Điểm chấm phải là bội của {POINT_STEP}, ví dụ 0.25, 0.5, 1.75."
            )
        return point


class GradeSubmissionSerializer(serializers.Serializer):
    answers = GradeAnswerItemSerializer(many=True)

    def validate_answers(self, answers):
        if len(answers) > MAX_QUESTIONS_PER_ASSIGNMENT:
            raise serializers.ValidationError(
                f"Mỗi lần gửi tối đa {MAX_QUESTIONS_PER_ASSIGNMENT} câu."
            )
        return answers

    def validate(self, attrs):
        submission = self.instance
        answers = attrs["answers"]

        if submission.submitted_at is None:
            raise serializers.ValidationError(
                "Bài làm này chưa được nộp nên chưa thể chấm."
            )

        owned_ids = set(submission.stu_answers.values_list("id", flat=True))
        unknown_ids = [item["id"] for item in answers if item["id"] not in owned_ids]

        if unknown_ids:
            raise serializers.ValidationError(
                {"answers": f"Các câu trả lời {unknown_ids} không thuộc bài nộp này."}
            )

        max_points = {
            stu_answer.id: stu_answer.question.point
            for stu_answer in submission.stu_answers.select_related("question")
        }

        for item in answers:
            max_point = max_points[item["id"]]
            if item["point"] > max_point:
                raise serializers.ValidationError(
                    {"answers": f"Câu trả lời {item['id']} tối đa {max_point} điểm."}
                )

        return attrs


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

        if not assignment.questions.exists():
            raise serializers.ValidationError(
                "Bài tập chưa có câu hỏi nào nên chưa thể công khai."
            )

        unset_count = count_questions_without_point(assignment)

        if unset_count:
            raise serializers.ValidationError(f"Còn {unset_count} câu chưa đặt điểm.")

        total_points = total_question_points(assignment)

        if total_points != TOTAL_SCORE:
            raise serializers.ValidationError(
                f"Tổng điểm các câu đang là {total_points}, phải đủ {TOTAL_SCORE} "
                "mới công khai được."
            )

        return attrs

    def update(self, instance, validated_data):
        instance.published_at = timezone.now()
        instance.save(update_fields=["published_at", "updated_at"])
        return instance
