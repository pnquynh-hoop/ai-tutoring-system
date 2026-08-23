from decimal import Decimal

import pytest
from model_bakery import baker
from rest_framework.exceptions import ValidationError


from assignments.models import Question, StudentAnswer
from assignments.services import grade_submission, start_attempt, submit_assignment


def make_submission(student, answers, assignment):
    start_attempt(student=student, assignment=assignment)
    return submit_assignment(student=student, assignment=assignment, answers=answers)


def run_grade(submission, answers):
    return grade_submission(submission=submission, answers=answers)


@pytest.fixture
def essay_assignment(assignment):
    choice = baker.make(
        Question,
        assignment=assignment,
        question_type=Question.QuestionType.MULTIPLE_CHOICE,
        order=1,
    )
    right = baker.make(
        "assignments.Answer", question=choice, content="Đúng", is_correct=True
    )
    baker.make("assignments.Answer", question=choice, content="Sai", is_correct=False)
    essay = baker.make(
        Question,
        assignment=assignment,
        question_type=Question.QuestionType.ESSAY,
        order=2,
    )
    return assignment, choice, right, essay


@pytest.mark.django_db
class TestGradeSubmission:
    def submit(self, student, data):
        assignment, choice, right, essay = data
        return make_submission(
            student,
            [
                {"question_id": choice.id, "answer_id": right.id},
                {"question_id": essay.id, "answer_text": "Bài làm của em"},
            ],
            assignment,
        )

    def test_essay_submission_starts_ungraded(self, essay_assignment, enrolled_student):
        submission = self.submit(enrolled_student, essay_assignment)

        assert submission.score is None
        assert submission.stu_answers.filter(point__isnull=True).count() == 1

    def test_grading_essay_completes_the_score(
        self, essay_assignment, enrolled_student
    ):
        submission = self.submit(enrolled_student, essay_assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        graded = run_grade(
            submission,
            [{"id": essay_answer.id, "point": Decimal("5"), "tutor_comment": "Tốt"}],
        )

        assert graded.score == Decimal("10.0")
        essay_answer.refresh_from_db()
        assert essay_answer.tutor_comment == "Tốt"

    def test_partial_grading_keeps_score_null(self, essay_assignment, enrolled_student):
        submission = self.submit(enrolled_student, essay_assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        graded = run_grade(
            submission, [{"id": essay_answer.id, "point": Decimal("2.5")}]
        )
        assert graded.score == Decimal("7.5")

        StudentAnswer.objects.filter(submission=submission).exclude(
            pk=essay_answer.pk
        ).update(point=None)
        regraded = run_grade(
            submission, [{"id": essay_answer.id, "point": Decimal("2.5")}]
        )
        assert regraded.score is None

    def test_point_cannot_exceed_max_per_question(
        self, essay_assignment, enrolled_student
    ):
        submission = self.submit(enrolled_student, essay_assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        with pytest.raises(ValidationError):
            run_grade(submission, [{"id": essay_answer.id, "point": Decimal("6")}])

    def test_answer_from_other_submission_is_rejected(
        self, essay_assignment, enrolled_student, make_student, course
    ):
        submission = self.submit(enrolled_student, essay_assignment)
        other = make_student()
        baker.make("courses.Enrollment", course=course, student=other)
        other_submission = self.submit(other, essay_assignment)
        foreign_answer = other_submission.stu_answers.first()

        with pytest.raises(ValidationError):
            run_grade(submission, [{"id": foreign_answer.id, "point": Decimal("1")}])

    def test_three_questions_full_marks_reaches_ten(
        self, assignment, enrolled_student
    ):
        answers = []
        for order in (1, 2):
            choice = baker.make(
                Question,
                assignment=assignment,
                question_type=Question.QuestionType.MULTIPLE_CHOICE,
                order=order,
            )
            right = baker.make(
                "assignments.Answer", question=choice, content="Đúng", is_correct=True
            )
            answers.append({"question_id": choice.id, "answer_id": right.id})

        essay = baker.make(
            Question,
            assignment=assignment,
            question_type=Question.QuestionType.ESSAY,
            order=3,
        )
        answers.append({"question_id": essay.id, "answer_text": "Bài làm của em"})

        submission = make_submission(enrolled_student, answers, assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        graded = run_grade(submission, [{"id": essay_answer.id, "point": Decimal("3.33")}])

        assert graded.score == Decimal("10.0")

    def test_cannot_grade_unsubmitted_attempt(self, assignment, enrolled_student):
        attempt = baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            submitted_at=None,
        )

        with pytest.raises(ValidationError):
            run_grade(attempt, [])
