from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from assignments.models import Question, Submission
from assignments.serializers import StartAttemptSerializer, SubmitAssignmentSerializer
from assignments.services import (
    MAX_ATTEMPTS,
    count_used_attempts,
    finalize_attempt,
    save_answer_draft,
    start_attempt,
    submit_assignment,
)


def make_context(student):
    return {"request": SimpleNamespace(user=student)}


def run_start(student, assignment):
    serializer = StartAttemptSerializer(
        assignment, data={}, context=make_context(student)
    )
    serializer.is_valid(raise_exception=True)
    return start_attempt(
        student=student,
        assignment=assignment,
        open_attempt=serializer.validated_data["open_attempt"],
    )


def run_submit_only(student, assignment, answers):
    serializer = SubmitAssignmentSerializer(
        assignment, data={"answers": answers}, context=make_context(student)
    )
    serializer.is_valid(raise_exception=True)
    return submit_assignment(
        student=student,
        assignment=assignment,
        answers=serializer.validated_data["answers"],
    )


def run_submit(student, answers, assignment):
    run_start(student, assignment)
    return run_submit_only(student, assignment, answers)


def run_save_draft(student, assignment, answers):
    serializer = SubmitAssignmentSerializer(
        assignment, data={"answers": answers}, context=make_context(student)
    )
    serializer.is_valid(raise_exception=True)
    return save_answer_draft(
        student=student,
        assignment=assignment,
        answers=serializer.validated_data["answers"],
    )


@pytest.mark.django_db
class TestSubmitAssignment:
    def make_choice_question(
        self, assignment, order, correct="A", wrong="B", point=Decimal("5")
    ):
        question = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.MULTIPLE_CHOICE,
            order=order,
            point=point,
        )
        right = baker.make(
            "assignments.Answer", question=question, content=correct, is_correct=True
        )
        bad = baker.make(
            "assignments.Answer", question=question, content=wrong, is_correct=False
        )
        return question, right, bad

    def make_fill_question(
        self, assignment, order, correct="Hà Nội", point=Decimal("5")
    ):
        question = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.FILL_IN_BLANK,
            order=order,
            point=point,
        )
        baker.make(
            "assignments.Answer", question=question, content=correct, is_correct=True
        )
        return question

    def test_all_correct_gives_full_score(self, student, assignment):
        answers = []
        points = [Decimal("3.5"), Decimal("3.25"), Decimal("3.25")]
        for order, point in enumerate(points, start=1):
            question, right, _ = self.make_choice_question(
                assignment, order, point=point
            )
            answers.append({"question_id": question.id, "answer_id": right.id})

        submission = run_submit(student, answers, assignment)

        assert submission.score == Decimal("10.0")
        assert submission.submitted_at is not None

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

    def test_unanswered_question_scores_zero(self, student, assignment):
        q1, right1, _ = self.make_choice_question(assignment, 1)
        self.make_choice_question(assignment, 2)

        submission = run_submit(
            student, [{"question_id": q1.id, "answer_id": right1.id}], assignment
        )

        assert submission.score == Decimal("5.0")
        assert submission.stu_answers.count() == 2

        blank = submission.stu_answers.exclude(question=q1).get()
        assert blank.answer is None
        assert blank.point == Decimal("0")

    def test_fill_in_blank_is_case_insensitive(self, student, assignment):
        question = self.make_fill_question(assignment, 1, point=Decimal("10"))

        submission = run_submit(
            student,
            [{"question_id": question.id, "answer_text": "  hà nội "}],
            assignment,
        )

        assert submission.score == Decimal("10.0")

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

    def test_answer_from_other_question_raises(self, student, assignment):
        q1, _, _ = self.make_choice_question(assignment, 1)
        _, foreign_right, _ = self.make_choice_question(assignment, 2)

        with pytest.raises(ValidationError):
            run_submit(
                student,
                [{"question_id": q1.id, "answer_id": foreign_right.id}],
                assignment,
            )

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
            run_submit_only(
                student,
                assignment,
                [{"question_id": question.id, "answer_id": right.id}],
            )

    def test_submit_within_time_limit_succeeds(self, student):
        assignment = baker.make(
            "assignments.Assignment",
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=30,
        )
        question, right, _ = self.make_choice_question(
            assignment, 1, point=Decimal("10")
        )
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now() - timedelta(minutes=5),
        )

        submission = run_submit_only(
            student,
            assignment,
            [{"question_id": question.id, "answer_id": right.id}],
        )

        assert submission.id == attempt.id
        assert submission.score == Decimal("10.0")

    def test_start_attempt_reuses_open_attempt(self, student, assignment):
        self.make_choice_question(assignment, 1)

        first = run_start(student, assignment)
        second = run_start(student, assignment)

        assert first.id == second.id
        assert (
            Submission.objects.filter(assignment=assignment, student=student).count()
            == 1
        )

    def test_new_attempt_after_submit(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)

        first = run_start(student, assignment)
        run_submit(
            student, [{"question_id": question.id, "answer_id": right.id}], assignment
        )
        second = run_start(student, assignment)

        assert first.id != second.id
        assert Submission.objects.filter(submitted_at__isnull=False).count() == 1

    def test_cannot_submit_more_than_max_attempts(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)
        answers = [{"question_id": question.id, "answer_id": right.id}]

        for _ in range(MAX_ATTEMPTS):
            run_submit(student, answers, assignment)

        with pytest.raises(ValidationError):
            run_submit(student, answers, assignment)

        assert count_used_attempts(student, assignment) == MAX_ATTEMPTS

    def test_cannot_start_more_than_max_attempts(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)
        answers = [{"question_id": question.id, "answer_id": right.id}]

        for _ in range(MAX_ATTEMPTS):
            run_submit(student, answers, assignment)

        with pytest.raises(ValidationError):
            run_start(student, assignment)

    def test_attempt_limit_is_per_student(self, student, assignment):
        question, right, _ = self.make_choice_question(
            assignment, 1, point=Decimal("10")
        )
        answers = [{"question_id": question.id, "answer_id": right.id}]
        other_student = baker.make("accounts.User")

        for _ in range(MAX_ATTEMPTS):
            run_submit(student, answers, assignment)

        submission = run_submit(other_student, answers, assignment)

        assert submission.score == Decimal("10.0")
        assert count_used_attempts(other_student, assignment) == 1

    def test_submit_without_start_raises(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)

        with pytest.raises(ValidationError):
            run_submit_only(
                student,
                assignment,
                [{"question_id": question.id, "answer_id": right.id}],
            )

        assert not Submission.objects.filter(
            assignment=assignment, student=student
        ).exists()

    def test_start_closes_expired_attempt_and_opens_new_one(self, student):
        assignment = baker.make(
            "assignments.Assignment",
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=30,
        )
        self.make_choice_question(assignment, 1)
        expired = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now() - timedelta(minutes=31),
        )

        attempt = run_start(student, assignment)

        expired.refresh_from_db()
        assert attempt.id != expired.id
        assert attempt.submitted_at is None
        assert expired.submitted_at == expired.deadline
        assert expired.score == Decimal("0.0")
        assert count_used_attempts(student, assignment) == 2


@pytest.mark.django_db
class TestSaveDraftAndFinalize:
    def make_choice_question(
        self, assignment, order, correct="A", wrong="B", point=Decimal("5")
    ):
        question = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.MULTIPLE_CHOICE,
            order=order,
            point=point,
        )
        right = baker.make(
            "assignments.Answer", question=question, content=correct, is_correct=True
        )
        bad = baker.make(
            "assignments.Answer", question=question, content=wrong, is_correct=False
        )
        return question, right, bad

    def test_saving_same_question_twice_keeps_one_row(self, student, assignment):
        question, right, wrong = self.make_choice_question(assignment, 1)
        run_start(student, assignment)

        run_save_draft(
            student, assignment, [{"question_id": question.id, "answer_id": wrong.id}]
        )
        attempt = run_save_draft(
            student, assignment, [{"question_id": question.id, "answer_id": right.id}]
        )

        assert attempt.stu_answers.count() == 1
        assert attempt.stu_answers.first().answer_id == right.id

    def test_draft_leaves_attempt_open_and_unscored(self, student, assignment):
        question, right, _ = self.make_choice_question(assignment, 1)
        run_start(student, assignment)

        attempt = run_save_draft(
            student, assignment, [{"question_id": question.id, "answer_id": right.id}]
        )

        assert attempt.submitted_at is None
        assert attempt.score is None
        assert attempt.stu_answers.first().point is None

    def test_finalize_grades_rows_saved_as_draft(self, student, assignment):
        q1, right1, _ = self.make_choice_question(assignment, 1)
        q2, _, wrong2 = self.make_choice_question(assignment, 2)
        attempt = run_start(student, assignment)

        run_save_draft(
            student,
            assignment,
            [
                {"question_id": q1.id, "answer_id": right1.id},
                {"question_id": q2.id, "answer_id": wrong2.id},
            ],
        )
        deadline = timezone.now()
        finalize_attempt(attempt, deadline)

        attempt.refresh_from_db()
        assert attempt.score == Decimal("5.0")
        assert attempt.submitted_at == deadline

    def test_finalize_twice_keeps_the_first_result(self, student, assignment):
        question, right, _ = self.make_choice_question(
            assignment, 1, point=Decimal("10")
        )
        attempt = run_start(student, assignment)
        run_save_draft(
            student, assignment, [{"question_id": question.id, "answer_id": right.id}]
        )

        first_submitted_at = timezone.now() - timedelta(minutes=5)
        finalize_attempt(attempt, first_submitted_at)
        finalize_attempt(Submission.objects.get(pk=attempt.pk), timezone.now())

        attempt.refresh_from_db()
        assert attempt.submitted_at == first_submitted_at
        assert attempt.score == Decimal("10.0")

    def test_finalize_without_any_draft_scores_zero(self, student, assignment):
        self.make_choice_question(assignment, 1)
        attempt = run_start(student, assignment)

        finalize_attempt(attempt, timezone.now())

        attempt.refresh_from_db()
        assert attempt.score == Decimal("0.0")
