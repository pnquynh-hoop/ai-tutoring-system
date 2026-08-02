from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import SimpleUserSerializer
from assignments.models import Answer, Assignment, Question, StudentAnswer, Submission

TOTAL_SCORE = Decimal("10")
SUBMIT_GRACE = timedelta(seconds=30)
MAX_ATTEMPTS = 3


def count_submitted_attempts(student, assignment) -> int:
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=False
    ).count()


def get_open_attempt(student, assignment):
    """Lượt làm bài đang dở (chưa nộp) gần nhất của học sinh, nếu có."""
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=True
    ).first()


def point_per_question(assignment) -> Decimal:
    """Điểm tối đa mỗi câu, cũng là trần khi gia sư chấm tay."""
    total = assignment.questions.count()
    if not total:
        return Decimal(0)
    return (TOTAL_SCORE / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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


def _validate_open_attempt(student, assignment):
    """Lượt làm bài phải còn hạn mức hoặc còn trong thời gian của lượt đang mở."""
    attempt = get_open_attempt(student, assignment)

    if attempt is None:
        if count_submitted_attempts(student, assignment) >= MAX_ATTEMPTS:
            raise serializers.ValidationError(
                f"Bạn đã dùng hết {MAX_ATTEMPTS} lượt làm bài của bài tập này."
            )
        return

    deadline = attempt.deadline
    if deadline and timezone.now() > deadline + SUBMIT_GRACE:
        raise serializers.ValidationError("Đã hết thời gian làm bài của lượt làm này.")


def _open_or_create_attempt(student, assignment):
    """Lấy lượt đang làm dở, chưa có thì mở lượt mới với mốc giờ của server."""
    attempt = get_open_attempt(student, assignment)
    if attempt is None:
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now(),
            score=None,
        )
    return attempt


class StartAttemptSerializer(serializers.Serializer):
    """Mở lượt làm bài. Không có field đầu vào.

    Cần context ``assignment`` và ``student``.
    """

    def validate(self, attrs):
        assignment = self.context["assignment"]

        if assignment.due_date and timezone.now() > assignment.due_date:
            raise serializers.ValidationError("Bài tập đã hết hạn nộp.")

        if not assignment.questions.exists():
            raise serializers.ValidationError("Bài tập chưa có câu hỏi nào.")

        _validate_open_attempt(self.context["student"], assignment)
        return attrs

    def create(self, validated_data):
        return _open_or_create_attempt(
            self.context["student"], self.context["assignment"]
        )


class SubmitAssignmentSerializer(serializers.Serializer):
    """Cần context ``assignment`` và ``student``."""

    answers = SubmitAnswerItemSerializer(many=True)

    def validate(self, attrs):
        assignment = self.context["assignment"]
        answers = attrs["answers"]

        if assignment.due_date and timezone.now() > assignment.due_date:
            raise serializers.ValidationError("Bài tập đã hết hạn nộp.")

        questions = {q.id: q for q in assignment.questions.prefetch_related("answers")}
        if not questions:
            raise serializers.ValidationError("Bài tập chưa có câu hỏi nào.")

        question_ids = [item["question_id"] for item in answers]

        unknown_ids = [qid for qid in question_ids if qid not in questions]
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

        _validate_open_attempt(self.context["student"], assignment)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        student = self.context["student"]
        assignment = self.context["assignment"]

        questions = {q.id: q for q in assignment.questions.prefetch_related("answers")}
        total_questions = len(questions)
        # Giữ nguyên phần thập phân khi cộng dồn, chỉ làm tròn ở điểm tổng.
        point_per_answer = (
            TOTAL_SCORE / total_questions if total_questions else Decimal(0)
        )

        # Lượt làm bài phải được start trước để tính giờ; client nộp thẳng thì tạo mới.
        attempt = _open_or_create_attempt(student, assignment)

        stu_answers = []
        has_essay = False
        earned_score = Decimal(0)

        for item in validated_data["answers"]:
            question = questions[item["question_id"]]
            stu_answer = StudentAnswer(question=question, submission=attempt)
            stu_answers.append(stu_answer)

            if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
                selected = next(
                    (a for a in question.answers.all() if a.id == item.get("answer_id")),
                    None,
                )
                stu_answer.answer = selected
                earned = (
                    point_per_answer
                    if (selected and selected.is_correct)
                    else Decimal(0)
                )

            elif question.question_type == Question.QuestionType.FILL_IN_BLANK:
                text = (item.get("answer_text") or "").strip()
                stu_answer.answer_text = text
                correct = next(
                    (a for a in question.answers.all() if a.is_correct), None
                )
                earned = (
                    point_per_answer
                    if correct and text.lower() == correct.content.strip().lower()
                    else Decimal(0)
                )

            else:  # ESSAY: để trống điểm, chờ gia sư chấm tay
                stu_answer.answer_text = (item.get("answer_text") or "").strip()
                stu_answer.point = None
                has_essay = True
                continue

            stu_answer.point = earned.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            earned_score += earned

        StudentAnswer.objects.bulk_create(stu_answers)

        attempt.submitted_at = timezone.now()
        # Còn câu tự luận thì để điểm trống chờ gia sư chấm.
        attempt.score = (
            None
            if has_essay
            else earned_score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        )
        attempt.save(update_fields=["score", "submitted_at"])
        return attempt


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
    deadline = serializers.DateTimeField(read_only=True, allow_null=True)
    time_limit_minutes = serializers.IntegerField(
        source="assignment.time_limit_minutes", read_only=True, allow_null=True
    )

    class Meta:
        model = Submission
        fields = ["id", "assignment", "started_at", "deadline", "time_limit_minutes"]


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
        return float(point_per_question(obj.assignment))


class GradeAnswerItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID của StudentAnswer cần chấm")
    point = serializers.DecimalField(
        max_digits=4, decimal_places=2, min_value=Decimal("0")
    )
    tutor_comment = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class GradeSubmissionSerializer(serializers.Serializer):
    """Gia sư chấm tay. Khởi tạo với instance là Submission cần chấm."""

    answers = GradeAnswerItemSerializer(many=True)

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

        max_point = point_per_question(submission.assignment)
        if any(item["point"] > max_point for item in answers):
            raise serializers.ValidationError(
                {"answers": f"Điểm mỗi câu tối đa là {max_point}."}
            )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        stu_answers = {
            answer.id: answer
            for answer in instance.stu_answers.select_related("question")
        }

        graded = []
        for item in validated_data["answers"]:
            answer = stu_answers[item["id"]]
            answer.point = item["point"]
            if "tutor_comment" in item:
                answer.tutor_comment = item["tutor_comment"]
            graded.append(answer)

        StudentAnswer.objects.bulk_update(graded, ["point", "tutor_comment"])

        # Còn câu chưa có điểm thì bài vẫn ở trạng thái chờ chấm.
        all_points = [answer.point for answer in stu_answers.values()]
        if any(point is None for point in all_points):
            instance.score = None
        else:
            instance.score = sum(all_points, Decimal(0)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )

        instance.save(update_fields=["score"])
        return instance
