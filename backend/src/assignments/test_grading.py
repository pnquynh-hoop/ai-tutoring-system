from decimal import Decimal

import pytest
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from core.testing import auth_client

from .models import Question, StudentAnswer
from .serializers import GradeSubmissionSerializer, SubmitAssignmentSerializer


def run_submit(student, answers, assignment):
    """Nộp bài qua đúng luồng của view."""
    serializer = SubmitAssignmentSerializer(
        data={"answers": answers},
        context={"assignment": assignment, "student": student},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def run_grade(submission, answers):
    """Chấm bài qua đúng luồng của view."""
    serializer = GradeSubmissionSerializer(submission, data={"answers": answers})
    serializer.is_valid(raise_exception=True)
    return serializer.save()


@pytest.fixture
def essay_assignment(assignment):
    """Bài tập 2 câu: 1 trắc nghiệm chấm tự động, 1 tự luận chờ chấm tay."""
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
        return run_submit(
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

        # 1 câu trắc nghiệm đúng (5đ) + 5đ tự luận = 10đ
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

        # Xoá điểm một câu khác thì bài quay lại trạng thái chờ chấm.
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
            run_grade(
                submission, [{"id": essay_answer.id, "point": Decimal("6")}]
            )

    def test_answer_from_other_submission_is_rejected(
        self, essay_assignment, enrolled_student, make_student, course
    ):
        submission = self.submit(enrolled_student, essay_assignment)
        other = make_student()
        baker.make("courses.Enrollment", course=course, student=other)
        other_submission = self.submit(other, essay_assignment)
        foreign_answer = other_submission.stu_answers.first()

        with pytest.raises(ValidationError):
            run_grade(
                submission, [{"id": foreign_answer.id, "point": Decimal("1")}]
            )

    def test_cannot_grade_unsubmitted_attempt(self, assignment, enrolled_student):
        attempt = baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            submitted_at=None,
        )

        with pytest.raises(ValidationError):
            run_grade(attempt, [])


@pytest.mark.django_db
class TestGradeApi:
    def make_submission(self, student, data):
        assignment, choice, right, essay = data
        return run_submit(
            student,
            [
                {"question_id": choice.id, "answer_id": right.id},
                {"question_id": essay.id, "answer_text": "Bài làm"},
            ],
            assignment,
        )

    def test_tutor_can_grade_via_api(self, essay_assignment, enrolled_student, course):
        submission = self.make_submission(enrolled_student, essay_assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        response = auth_client(course.tutor).patch(
            f"/api/v1/submissions/{submission.pk}/grade/",
            {
                "answers": [
                    {"id": essay_answer.id, "point": "4.5", "tutor_comment": "Khá"}
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert float(response.data["score"]) == 9.5

    def test_student_cannot_grade(self, essay_assignment, enrolled_student):
        submission = self.make_submission(enrolled_student, essay_assignment)
        essay_answer = submission.stu_answers.get(point__isnull=True)

        response = auth_client(enrolled_student).patch(
            f"/api/v1/submissions/{submission.pk}/grade/",
            {"answers": [{"id": essay_answer.id, "point": "5"}]},
            format="json",
        )

        assert response.status_code == 403

    def test_other_tutor_cannot_grade(
        self, essay_assignment, enrolled_student, make_tutor
    ):
        submission = self.make_submission(enrolled_student, essay_assignment)

        response = auth_client(make_tutor()).patch(
            f"/api/v1/submissions/{submission.pk}/grade/",
            {"answers": []},
            format="json",
        )

        assert response.status_code in (403, 404)

    def test_submission_detail_exposes_answers_for_review(
        self, essay_assignment, enrolled_student
    ):
        submission = self.make_submission(enrolled_student, essay_assignment)

        response = auth_client(enrolled_student).get(
            f"/api/v1/submissions/{submission.pk}/"
        )

        assert response.status_code == 200
        assert len(response.data["stu_answers"]) == 2
        assert response.data["point_per_question"] == 5.0
