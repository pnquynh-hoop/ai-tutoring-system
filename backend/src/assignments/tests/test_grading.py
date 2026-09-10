from decimal import Decimal
from types import SimpleNamespace

import pytest
from model_bakery import baker
from rest_framework.exceptions import ValidationError


from assignments.models import Question, StudentAnswer
from assignments.serializers import (
    GradeSubmissionSerializer,
    StartAttemptSerializer,
    SubmitAssignmentSerializer,
)
from assignments.services import grade_submission, start_attempt, submit_assignment


def make_context(student):
    return {"request": SimpleNamespace(user=student)}


def make_submission(student, answers, assignment):
    start_serializer = StartAttemptSerializer(
        assignment, data={}, context=make_context(student)
    )
    start_serializer.is_valid(raise_exception=True)
    start_attempt(
        student=student,
        assignment=assignment,
        open_attempt=start_serializer.validated_data["open_attempt"],
    )

    submit_serializer = SubmitAssignmentSerializer(
        assignment, data={"answers": answers}, context=make_context(student)
    )
    submit_serializer.is_valid(raise_exception=True)
    return submit_assignment(
        student=student,
        assignment=assignment,
        answers=submit_serializer.validated_data["answers"],
    )


def run_grade(submission, answers):
    serializer = GradeSubmissionSerializer(submission, data={"answers": answers})
    serializer.is_valid(raise_exception=True)
    return grade_submission(
        submission=submission, answers=serializer.validated_data["answers"]
    )


@pytest.fixture
def essay_assignment(assignment):
    choice = baker.make(
        Question,
        assignment=assignment,
        question_type=Question.QuestionType.MULTIPLE_CHOICE,
        order=1,
        point=Decimal("5"),
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
        point=Decimal("5"),
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
        self, essay_assignment, enrolled_student, student_group, course
    ):
        submission = self.submit(enrolled_student, essay_assignment)
        other = baker.make("accounts.User")
        other.groups.add(student_group)
        baker.make("courses.Enrollment", course=course, student=other)
        other_submission = self.submit(other, essay_assignment)
        foreign_answer = other_submission.stu_answers.first()

        with pytest.raises(ValidationError):
            run_grade(submission, [{"id": foreign_answer.id, "point": Decimal("1")}])

    def test_three_questions_full_marks_reaches_ten(
        self, assignment, enrolled_student
    ):
        answers = []
        for order, point in ((1, Decimal("3.5")), (2, Decimal("3.25"))):
            choice = baker.make(
                Question,
                assignment=assignment,
                question_type=Question.QuestionType.MULTIPLE_CHOICE,
                order=order,
                point=point,
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
            point=Decimal("3.25"),
        )
        answers.append({"question_id": essay.id, "answer_text": "Bài làm của em"})

        submission = make_submission(enrolled_student, answers, assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        graded = run_grade(
            submission, [{"id": essay_answer.id, "point": Decimal("3.25")}]
        )

        assert graded.score == Decimal("10.0")

    def test_point_off_the_step_is_rejected(self, essay_assignment, enrolled_student):
        submission = self.submit(enrolled_student, essay_assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        with pytest.raises(ValidationError):
            run_grade(submission, [{"id": essay_answer.id, "point": Decimal("3.33")}])

    def test_cannot_grade_unsubmitted_attempt(self, assignment, enrolled_student):
        attempt = baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            submitted_at=None,
        )

        with pytest.raises(ValidationError):
            run_grade(attempt, [])
