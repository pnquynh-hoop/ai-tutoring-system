from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from .models import Question, Submission
from .serializers import (
    MAX_ATTEMPTS,
    StartAttemptSerializer,
    SubmitAssignmentSerializer,
    count_submitted_attempts,
)


def run_submit(student, answers, assignment):
    """Nộp bài qua đúng luồng của view."""
    serializer = SubmitAssignmentSerializer(
        data={"answers": answers},
        context={"assignment": assignment, "student": student},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def run_start(student, assignment):
    """Mở lượt làm bài qua đúng luồng của view."""
    serializer = StartAttemptSerializer(
        data={}, context={"assignment": assignment, "student": student}
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


@pytest.mark.django_db
class TestSubmitAssignment:
    @pytest.fixture
    def student(self):
        return baker.make("accounts.User")

    @pytest.fixture
    def assignment(self):
        return baker.make(
            "assignments.Assignment",
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=None,
        )

    def make_choice_question(self, assignment, order, correct="A", wrong="B"):
        question = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.MULTIPLE_CHOICE,
            order=order,
        )
        right = baker.make(
            "assignments.Answer", question=question, content=correct, is_correct=True
        )
        bad = baker.make(
            "assignments.Answer", question=question, content=wrong, is_correct=False
        )
        return question, right, bad

    def make_fill_question(self, assignment, order, correct="Hà Nội"):
        question = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.FILL_IN_BLANK,
            order=order,
        )
        baker.make(
            "assignments.Answer", question=question, content=correct, is_correct=True
        )
        return question

    # ---------- CASE 1: đúng hết phải được trọn 10 điểm ----------
    def test_all_correct_gives_full_score(self, student, assignment):
        answers = []
        for order in range(1, 4):  # 3 câu: 10/3 không chia hết
            question, right, _ = self.make_choice_question(assignment, order)
            answers.append({"question_id": question.id, "answer_id": right.id})

        submission = run_submit(student, answers, assignment)

        assert submission.score == Decimal("10.0")
        assert submission.submitted_at is not None

    # ---------- CASE 2: sai một câu ----------
    def test_partial_correct_score(self, student, assignment):
        q1, right1, _ = self.make_choice_question(assignment, 1)
        q2, _, wrong2 = self.make_choice_question(assignment, 2)

        submission = run_submit(
            student,
            [
                {"question_id": q1.id, "answer_id": right1.id},
                {"question_id": q2.id, "answer_id": wrong2.id},
            ],
            assignment,
        )

        assert submission.score == Decimal("5.0")

    # ---------- CASE 3: không trả lời thì không được điểm ----------
    def test_unanswered_question_scores_zero(self, student, assignment):
        q1, right1, _ = self.make_choice_question(assignment, 1)
        self.make_choice_question(assignment, 2)

        submission = run_submit(
            student, [{"question_id": q1.id, "answer_id": right1.id}], assignment
        )

        assert submission.score == Decimal("5.0")
        assert submission.stu_answers.count() == 1

    # ---------- CASE 4: điền khuyết không phân biệt hoa thường/khoảng trắng ----------
    def test_fill_in_blank_is_case_insensitive(self, student, assignment):
        question = self.make_fill_question(assignment, 1)

        submission = run_submit(
            student,
            [{"question_id": question.id, "answer_text": "  hà nội "}],
            assignment,
        )

        assert submission.score == Decimal("10.0")

    # ---------- CASE 5: có câu tự luận thì chờ gia sư chấm ----------
    def test_essay_leaves_score_null(self, student, assignment):
        q1, right1, _ = self.make_choice_question(assignment, 1)
        essay = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.ESSAY,
            order=2,
        )

        submission = run_submit(
            student,
            [
                {"question_id": q1.id, "answer_id": right1.id},
                {"question_id": essay.id, "answer_text": "Bài làm của em"},
            ],
            assignment,
        )

        assert submission.score is None
        assert submission.submitted_at is not None

    # ---------- CASE 6: quá hạn nộp ----------
    def test_submit_after_due_date_raises(self, student):
        assignment = baker.make(
            "assignments.Assignment", due_date=timezone.now() - timedelta(minutes=1)
        )
        question, right, _ = self.make_choice_question(assignment, 1)

        with pytest.raises(ValidationError):
            run_submit(
                student,
                [{"question_id": question.id, "answer_id": right.id}],
                assignment,
            )

    # ---------- CASE 7: bài tập chưa có câu hỏi ----------
    def test_assignment_without_questions_raises(self, student, assignment):
        with pytest.raises(ValidationError):
            run_submit(student, [], assignment)

    # ---------- CASE 8: câu hỏi không thuộc bài tập ----------
    def test_unknown_question_id_raises(self, student, assignment):
        self.make_choice_question(assignment, 1)
        other_assignment = baker.make(
            "assignments.Assignment", due_date=timezone.now() + timedelta(days=1)
        )
        other_question, other_answer, _ = self.make_choice_question(other_assignment, 1)

        with pytest.raises(ValidationError):
            run_submit(
                student,
                [{"question_id": other_question.id, "answer_id": other_answer.id}],
                assignment,
            )

    # ---------- CASE 9: đáp án không thuộc câu hỏi ----------
    def test_answer_from_other_question_raises(self, student, assignment):
        q1, _, _ = self.make_choice_question(assignment, 1)
        _, foreign_right, _ = self.make_choice_question(assignment, 2)

        with pytest.raises(ValidationError):
            run_submit(
                student,
                [{"question_id": q1.id, "answer_id": foreign_right.id}],
                assignment,
            )

    # ---------- CASE 10: trả lời trùng câu hỏi ----------
    def test_duplicated_question_raises(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)

        with pytest.raises(ValidationError):
            run_submit(
                student,
                [
                    {"question_id": question.id, "answer_id": right.id},
                    {"question_id": question.id, "answer_id": right.id},
                ],
                assignment,
            )

    # ---------- CASE 11: hết giờ làm bài ----------
    def test_submit_after_time_limit_raises(self, student):
        assignment = baker.make(
            "assignments.Assignment",
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=30,
        )
        question, right, _ = self.make_choice_question(assignment, 1)
        Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now() - timedelta(minutes=31),
        )

        with pytest.raises(ValidationError):
            run_submit(
                student,
                [{"question_id": question.id, "answer_id": right.id}],
                assignment,
            )

    # ---------- CASE 12: còn trong thời gian làm bài ----------
    def test_submit_within_time_limit_succeeds(self, student):
        assignment = baker.make(
            "assignments.Assignment",
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=30,
        )
        question, right, _ = self.make_choice_question(assignment, 1)
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now() - timedelta(minutes=5),
        )

        submission = run_submit(
            student, [{"question_id": question.id, "answer_id": right.id}], assignment
        )

        assert submission.id == attempt.id
        assert submission.score == Decimal("10.0")

    # ---------- CASE 13: start_attempt dùng lại lượt đang làm dở ----------
    def test_start_attempt_reuses_open_attempt(self, student, assignment):
        self.make_choice_question(assignment, 1)

        first = run_start(student, assignment)
        second = run_start(student, assignment)

        assert first.id == second.id
        assert (
            Submission.objects.filter(assignment=assignment, student=student).count()
            == 1
        )

    # ---------- CASE 14: nộp xong thì lượt mới được tạo lại ----------
    def test_new_attempt_after_submit(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)

        first = run_start(student, assignment)
        run_submit(
            student, [{"question_id": question.id, "answer_id": right.id}], assignment
        )
        second = run_start(student, assignment)

        assert first.id != second.id
        assert Submission.objects.filter(submitted_at__isnull=False).count() == 1

    # ---------- CASE 15: hết lượt thì không nộp thêm được ----------
    def test_cannot_submit_more_than_max_attempts(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)
        answers = [{"question_id": question.id, "answer_id": right.id}]

        for _ in range(MAX_ATTEMPTS):
            run_submit(student, answers, assignment)

        with pytest.raises(ValidationError):
            run_submit(student, answers, assignment)

        assert count_submitted_attempts(student, assignment) == MAX_ATTEMPTS

    # ---------- CASE 16: hết lượt thì không start lượt mới được ----------
    def test_cannot_start_more_than_max_attempts(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)
        answers = [{"question_id": question.id, "answer_id": right.id}]

        for _ in range(MAX_ATTEMPTS):
            run_submit(student, answers, assignment)

        with pytest.raises(ValidationError):
            run_start(student, assignment)

    # ---------- CASE 17: giới hạn tính riêng theo từng học sinh ----------
    def test_attempt_limit_is_per_student(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)
        answers = [{"question_id": question.id, "answer_id": right.id}]
        other_student = baker.make("accounts.User")

        for _ in range(MAX_ATTEMPTS):
            run_submit(student, answers, assignment)

        submission = run_submit(other_student, answers, assignment)

        assert submission.score == Decimal("10.0")
        assert count_submitted_attempts(other_student, assignment) == 1
