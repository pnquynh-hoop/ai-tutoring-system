from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker

from assignments.models import Question, StudentAnswer, Submission
from assignments.services import close_overdue_attempts


def make_choice_question(assignment, point=Decimal("10")):
    question = baker.make(
        Question,
        assignment=assignment,
        question_type=Question.QuestionType.MULTIPLE_CHOICE,
        order=1,
        point=point,
    )
    right = baker.make(
        "assignments.Answer", question=question, content="Đúng", is_correct=True
    )
    baker.make("assignments.Answer", question=question, content="Sai", is_correct=False)
    return question, right


def make_open_attempt(student, assignment, started_at):
    return Submission.objects.create(
        assignment=assignment, student=student, started_at=started_at, score=None
    )


@pytest.mark.django_db
class TestCloseOverdueAttempts:
    def timed_assignment(self, minutes=30):
        return baker.make(
            "assignments.Assignment",
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=minutes,
        )

    def test_attempt_past_time_limit_is_closed_and_graded(self, student):
        assignment = self.timed_assignment()
        question, right = make_choice_question(assignment)
        attempt = make_open_attempt(
            student, assignment, timezone.now() - timedelta(minutes=40)
        )
        StudentAnswer.objects.create(
            submission=attempt, question=question, answer=right
        )

        assert close_overdue_attempts() == 1

        attempt.refresh_from_db()
        assert attempt.submitted_at == attempt.deadline
        assert attempt.score == Decimal("10")

    def test_attempt_of_untimed_assignment_closes_at_the_due_date(self, student):
        due_date = timezone.now() - timedelta(minutes=5)
        assignment = baker.make(
            "assignments.Assignment", due_date=due_date, time_limit_minutes=None
        )
        question, right = make_choice_question(assignment)
        attempt = make_open_attempt(
            student, assignment, timezone.now() - timedelta(hours=2)
        )
        StudentAnswer.objects.create(
            submission=attempt, question=question, answer=right
        )

        assert close_overdue_attempts() == 1

        attempt.refresh_from_db()
        assert attempt.submitted_at == due_date
        assert attempt.score == Decimal("10")

    def test_attempt_still_within_the_time_limit_is_left_open(self, student):
        assignment = self.timed_assignment()
        make_choice_question(assignment)
        attempt = make_open_attempt(
            student, assignment, timezone.now() - timedelta(minutes=5)
        )

        assert close_overdue_attempts() == 0

        attempt.refresh_from_db()
        assert attempt.submitted_at is None

    def test_attempt_inside_the_grace_period_is_left_open(self, student):
        assignment = self.timed_assignment()
        make_choice_question(assignment)
        started_at = timezone.now() - timedelta(minutes=30, seconds=10)
        attempt = make_open_attempt(student, assignment, started_at)

        assert close_overdue_attempts() == 0

        attempt.refresh_from_db()
        assert attempt.submitted_at is None

    def test_the_earlier_cutoff_wins(self, student):
        due_date = timezone.now() - timedelta(minutes=20)
        assignment = baker.make(
            "assignments.Assignment", due_date=due_date, time_limit_minutes=30
        )
        make_choice_question(assignment)
        attempt = make_open_attempt(
            student, assignment, timezone.now() - timedelta(minutes=25)
        )

        assert close_overdue_attempts() == 1

        attempt.refresh_from_db()
        assert attempt.submitted_at == due_date

    def test_submitted_attempt_is_not_touched_again(self, student):
        assignment = self.timed_assignment()
        make_choice_question(assignment)
        submitted_at = timezone.now() - timedelta(hours=3)
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now() - timedelta(hours=4),
            submitted_at=submitted_at,
            score=Decimal("7.5"),
        )

        assert close_overdue_attempts() == 0

        attempt.refresh_from_db()
        assert attempt.submitted_at == submitted_at
        assert attempt.score == Decimal("7.5")

    def test_essay_left_ungraded_keeps_the_score_null(self, student):
        assignment = self.timed_assignment()
        essay = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.ESSAY,
            order=1,
            point=Decimal("10"),
        )
        attempt = make_open_attempt(
            student, assignment, timezone.now() - timedelta(minutes=40)
        )
        StudentAnswer.objects.create(
            submission=attempt, question=essay, answer_text="Bài làm dở dang"
        )

        assert close_overdue_attempts() == 1

        attempt.refresh_from_db()
        assert attempt.submitted_at == attempt.deadline
        assert attempt.score is None
