from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from core.testing import auth_client

from .models import Answer, Assignment, Question


def due_date():
    return (timezone.now() + timedelta(days=3)).isoformat()


@pytest.mark.django_db
class TestAssignmentCrud:
    def test_course_tutor_can_create_assignment(self, chapter, course):
        response = auth_client(course.tutor).post(
            "/api/v1/assignments/",
            {
                "chapter": chapter.pk,
                "title": "Kiểm tra chương 1",
                "due_date": due_date(),
            },
            format="json",
        )

        assert response.status_code == 201
        assert Assignment.objects.filter(chapter=chapter).count() == 1

    def test_other_tutor_cannot_create_assignment(self, chapter, make_tutor):
        response = auth_client(make_tutor()).post(
            "/api/v1/assignments/",
            {"chapter": chapter.pk, "title": "Chen ngang", "due_date": due_date()},
            format="json",
        )

        assert response.status_code == 403
        assert not Assignment.objects.filter(title="Chen ngang").exists()

    def test_student_cannot_create_assignment(self, chapter, enrolled_student):
        response = auth_client(enrolled_student).post(
            "/api/v1/assignments/",
            {"chapter": chapter.pk, "title": "Học sinh tạo", "due_date": due_date()},
            format="json",
        )

        assert response.status_code == 403

    def test_one_assignment_per_chapter(self, chapter, course, assignment):
        response = auth_client(course.tutor).post(
            "/api/v1/assignments/",
            {"chapter": chapter.pk, "title": "Bài tập thứ hai", "due_date": due_date()},
            format="json",
        )

        # Assignment.chapter là OneToOne nên chương đã có bài tập thì không thêm được nữa.
        assert response.status_code == 400

    def test_tutor_can_update_and_delete(self, assignment, course):
        client = auth_client(course.tutor)

        updated = client.patch(
            f"/api/v1/assignments/{assignment.pk}/",
            {"title": "Tên mới", "time_limit_minutes": 45},
            format="json",
        )
        assert updated.status_code == 200
        assignment.refresh_from_db()
        assert assignment.title == "Tên mới"
        assert assignment.time_limit_minutes == 45

        deleted = client.delete(f"/api/v1/assignments/{assignment.pk}/")
        assert deleted.status_code == 204
        assert not Assignment.objects.filter(pk=assignment.pk).exists()


@pytest.mark.django_db
class TestQuestionCrud:
    def multiple_choice_payload(self, assignment):
        return {
            "assignment": assignment.pk,
            "content": "2 + 2 = ?",
            "question_type": "MULTIPLE_CHOICE",
            "explanation": "Cộng hai số",
            "answers": [
                {"content": "4", "is_correct": True},
                {"content": "5", "is_correct": False},
            ],
        }

    def test_tutor_creates_question_with_answers(self, assignment, course):
        response = auth_client(course.tutor).post(
            "/api/v1/questions/",
            self.multiple_choice_payload(assignment),
            format="json",
        )

        assert response.status_code == 201
        question = Question.objects.get(pk=response.data["id"])
        assert question.answers.count() == 2
        assert question.order == 1

    def test_order_auto_increments(self, assignment, course):
        client = auth_client(course.tutor)
        for _ in range(2):
            client.post(
                "/api/v1/questions/",
                self.multiple_choice_payload(assignment),
                format="json",
            )

        assert list(
            Question.objects.filter(assignment=assignment)
            .order_by("order")
            .values_list("order", flat=True)
        ) == [1, 2]

    def test_multiple_choice_requires_exactly_one_correct(self, assignment, course):
        payload = self.multiple_choice_payload(assignment)
        payload["answers"] = [
            {"content": "4", "is_correct": True},
            {"content": "5", "is_correct": True},
        ]

        response = auth_client(course.tutor).post(
            "/api/v1/questions/", payload, format="json"
        )

        assert response.status_code == 400
        assert "answers" in response.data

    def test_multiple_choice_requires_two_options(self, assignment, course):
        payload = self.multiple_choice_payload(assignment)
        payload["answers"] = [{"content": "4", "is_correct": True}]

        response = auth_client(course.tutor).post(
            "/api/v1/questions/", payload, format="json"
        )

        assert response.status_code == 400

    def test_essay_must_not_have_answers(self, assignment, course):
        payload = self.multiple_choice_payload(assignment)
        payload["question_type"] = "ESSAY"

        response = auth_client(course.tutor).post(
            "/api/v1/questions/", payload, format="json"
        )

        assert response.status_code == 400

    def test_update_replaces_answers(self, assignment, course):
        client = auth_client(course.tutor)
        created = client.post(
            "/api/v1/questions/",
            self.multiple_choice_payload(assignment),
            format="json",
        )
        question_id = created.data["id"]

        response = client.patch(
            f"/api/v1/questions/{question_id}/",
            {
                "content": "3 + 3 = ?",
                "answers": [
                    {"content": "6", "is_correct": True},
                    {"content": "7", "is_correct": False},
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        contents = set(
            Answer.objects.filter(question_id=question_id).values_list(
                "content", flat=True
            )
        )
        assert contents == {"6", "7"}

    def test_other_tutor_cannot_create_question(self, assignment, make_tutor):
        response = auth_client(make_tutor()).post(
            "/api/v1/questions/",
            self.multiple_choice_payload(assignment),
            format="json",
        )

        assert response.status_code == 403

    def test_student_cannot_list_questions_with_answers(
        self, assignment, enrolled_student
    ):
        response = auth_client(enrolled_student).get(
            f"/api/v1/questions/?assignment={assignment.pk}"
        )

        assert response.status_code == 403

    def test_list_requires_assignment_param(self, assignment, course):
        response = auth_client(course.tutor).get("/api/v1/questions/")

        assert response.status_code == 400

    def test_student_question_list_hides_correct_answer(
        self, assignment, course, enrolled_student
    ):
        auth_client(course.tutor).post(
            "/api/v1/questions/",
            self.multiple_choice_payload(assignment),
            format="json",
        )

        response = auth_client(enrolled_student).get(
            f"/api/v1/assignments/{assignment.pk}/questions/"
        )

        assert response.status_code == 200
        assert "explanation" not in response.data[0]
        assert "is_correct" not in response.data[0]["answers"][0]


@pytest.mark.django_db
class TestSubmissionListing:
    @pytest.fixture
    def submission(self, assignment, enrolled_student):
        return baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=None,
            submitted_at=timezone.now(),
        )

    def test_student_sees_only_own_submissions(self, submission, make_student, course):
        other = make_student()
        baker.make("courses.Enrollment", course=course, student=other)

        response = auth_client(other).get("/api/v1/submissions/")

        assert response.status_code == 200
        assert response.data == []

    def test_tutor_sees_submissions_of_own_courses(self, submission, course):
        response = auth_client(course.tutor).get("/api/v1/submissions/")

        assert response.status_code == 200
        assert [item["id"] for item in response.data] == [submission.pk]

    def test_tutor_does_not_see_other_course_submissions(self, submission, make_tutor):
        response = auth_client(make_tutor()).get("/api/v1/submissions/")

        assert response.status_code == 200
        assert response.data == []

    def test_unsubmitted_attempt_is_hidden(self, assignment, enrolled_student, course):
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            started_at=timezone.now(),
            submitted_at=None,
        )

        response = auth_client(course.tutor).get("/api/v1/submissions/")

        assert response.data == []
