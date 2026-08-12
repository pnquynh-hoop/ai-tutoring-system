import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from core.testing import auth_client, make_published


@pytest.mark.django_db
class TestCourseAccessPermissions:
    def test_user_without_group_is_blocked(self, course):
        """Tài khoản chưa gán nhóm bị chặn ở permission, không lọt vào queryset."""
        outsider = baker.make("accounts.User")

        response = auth_client(outsider).get("/api/v1/courses/")

        assert response.status_code == 403

    def test_anonymous_is_blocked(self, course):
        assert APIClient().get("/api/v1/courses/").status_code == 401

    def test_student_not_enrolled_cannot_read_course(self, course, make_student):
        response = auth_client(make_student()).get(f"/api/v1/courses/{course.pk}/")

        assert response.status_code in (403, 404)

    def test_enrolled_student_can_read_course(self, course, make_student):
        student = make_student()
        baker.make("courses.Enrollment", course=course, student=student)

        response = auth_client(student).get(f"/api/v1/courses/{course.pk}/")

        assert response.status_code == 200
        assert response.data["id"] == course.pk

    def test_inactive_enrollment_loses_access(self, course, make_student):
        student = make_student()
        baker.make(
            "courses.Enrollment", course=course, student=student, is_active=False
        )

        response = auth_client(student).get(f"/api/v1/courses/{course.pk}/")

        assert response.status_code in (403, 404)

    def test_student_not_enrolled_cannot_read_lesson(self, lesson, make_student):
        response = auth_client(make_student()).get(f"/api/v1/lessons/{lesson.pk}/")

        assert response.status_code == 403


@pytest.mark.django_db
class TestContentWritePermissions:
    def test_student_cannot_create_chapter(self, course, make_student):
        """IsTutor chặn ngay ở has_permission, chưa đụng tới serializer."""
        response = auth_client(make_student()).post(
            "/api/v1/chapters/",
            {"course": course.pk, "title": "Chương mới", "order": 9},
            format="json",
        )

        assert response.status_code == 403

    def test_tutor_cannot_create_chapter_in_other_course(self, course, make_tutor):
        """Gia sư khác bị chặn từ payload, trước khi bản ghi nào được tạo."""
        from courses.models import Chapter

        response = auth_client(make_tutor()).post(
            "/api/v1/chapters/",
            {"course": course.pk, "title": "Chương chen ngang", "order": 9},
            format="json",
        )

        assert response.status_code == 403
        assert not Chapter.objects.filter(title="Chương chen ngang").exists()

    def test_course_tutor_can_create_chapter(self, course):
        response = auth_client(course.tutor).post(
            "/api/v1/chapters/",
            {"course": course.pk, "title": "Chương hợp lệ", "order": 9},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["title"] == "Chương hợp lệ"

    def test_tutor_cannot_create_lesson_in_other_course(self, lesson, make_tutor):
        response = auth_client(make_tutor()).post(
            "/api/v1/lessons/",
            {"chapter": lesson.chapter_id, "title": "Bài chen ngang", "order": 9},
            format="json",
        )

        assert response.status_code == 403

    def test_tutor_cannot_delete_other_course_lesson(self, lesson, make_tutor):
        response = auth_client(make_tutor()).delete(f"/api/v1/lessons/{lesson.pk}/")

        assert response.status_code == 403


@pytest.mark.django_db
class TestResourcePermissions:
    def test_outsider_cannot_list_lesson_resources(self, lesson, make_student):
        make_published("courses.LearningResource", lesson=lesson)

        response = auth_client(make_student()).get(
            f"/api/v1/lessons/{lesson.pk}/resources/"
        )

        assert response.status_code == 403

    def test_enrolled_student_can_list_lesson_resources(self, lesson, make_student):
        student = make_student()
        baker.make("courses.Enrollment", course=lesson.chapter.course, student=student)
        make_published("courses.LearningResource", lesson=lesson)

        response = auth_client(student).get(f"/api/v1/lessons/{lesson.pk}/resources/")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_student_does_not_see_draft_resources(self, lesson, make_student):
        student = make_student()
        baker.make("courses.Enrollment", course=lesson.chapter.course, student=student)
        make_published("courses.LearningResource", lesson=lesson)
        baker.make("courses.LearningResource", lesson=lesson, published_at=None)

        response = auth_client(student).get(f"/api/v1/lessons/{lesson.pk}/resources/")

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_lesson_detail_hides_draft_resources(self, lesson, make_student):
        student = make_student()
        baker.make("courses.Enrollment", course=lesson.chapter.course, student=student)
        make_published("courses.LearningResource", lesson=lesson)
        baker.make("courses.LearningResource", lesson=lesson, published_at=None)

        response = auth_client(student).get(f"/api/v1/lessons/{lesson.pk}/")

        assert response.status_code == 200
        assert len(response.data["resources"]) == 1

    def test_tutor_sees_draft_resources(self, lesson):
        make_published("courses.LearningResource", lesson=lesson)
        baker.make("courses.LearningResource", lesson=lesson, published_at=None)

        response = auth_client(lesson.chapter.course.tutor).get(
            f"/api/v1/lessons/{lesson.pk}/resources/"
        )

        assert response.status_code == 200
        assert len(response.data) == 2

    def test_student_cannot_create_resource(self, lesson, make_student):
        student = make_student()
        baker.make("courses.Enrollment", course=lesson.chapter.course, student=student)

        response = auth_client(student).post(
            "/api/v1/resources/",
            {"lesson": lesson.pk, "title": "Tài liệu lạ", "resource_type": "OTHERS"},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestCommentPermissions:
    def test_enrolled_student_can_comment_and_author_comes_from_request(
        self, lesson, make_student
    ):
        student = make_student()
        baker.make("courses.Enrollment", course=lesson.chapter.course, student=student)

        response = auth_client(student).post(
            f"/api/v1/lessons/{lesson.pk}/comments/",
            {"content": "Em chưa hiểu bài", "created_by": 999},
            format="json",
        )

        assert response.status_code == 201
        # created_by luôn lấy từ request, giá trị client gửi lên bị bỏ qua.
        assert response.data["created_by"]["id"] == student.pk

    def test_student_cannot_mark_comment_as_right(self, lesson, make_student):
        student = make_student()
        baker.make("courses.Enrollment", course=lesson.chapter.course, student=student)
        comment = baker.make("courses.Comment", lesson=lesson, created_by=student)

        response = auth_client(student).post(
            f"/api/v1/comments/{comment.pk}/toggle-mark-right/"
        )

        assert response.status_code == 403

    def test_course_tutor_can_mark_comment_as_right(self, lesson, make_student, course):
        student = make_student()
        comment = baker.make("courses.Comment", lesson=lesson, created_by=student)

        response = auth_client(lesson.chapter.course.tutor).post(
            f"/api/v1/comments/{comment.pk}/toggle-mark-right/"
        )

        assert response.status_code == 200
        assert response.data["is_right"] is True


@pytest.mark.django_db
class TestAssignmentPermissions:
    @pytest.fixture
    def assignment(self, lesson):
        return make_published("assignments.Assignment", chapter=lesson.chapter)

    def test_outsider_cannot_read_assignment(self, assignment, make_student):
        response = auth_client(make_student()).get(
            f"/api/v1/assignments/{assignment.pk}/"
        )

        assert response.status_code == 403

    def test_outsider_cannot_read_questions(self, assignment, make_student):
        response = auth_client(make_student()).get(
            f"/api/v1/assignments/{assignment.pk}/questions/"
        )

        assert response.status_code == 403

    def test_enrolled_student_can_read_assignment(self, assignment, make_student):
        student = make_student()
        baker.make(
            "courses.Enrollment",
            course=assignment.chapter.course,
            student=student,
        )

        response = auth_client(student).get(f"/api/v1/assignments/{assignment.pk}/")

        assert response.status_code == 200

    def test_tutor_cannot_submit(self, assignment):
        tutor = assignment.chapter.course.tutor

        response = auth_client(tutor).post(
            f"/api/v1/assignments/{assignment.pk}/submit/",
            {"answers": []},
            format="json",
        )

        assert response.status_code == 403

    def test_student_cannot_read_other_student_submission(
        self, assignment, make_student
    ):
        owner, intruder = make_student(), make_student()
        for user in (owner, intruder):
            baker.make(
                "courses.Enrollment", course=assignment.chapter.course, student=user
            )
        submission = baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=owner,
            submitted_at="2026-01-01T00:00:00Z",
        )

        response = auth_client(intruder).get(f"/api/v1/submissions/{submission.pk}/")

        assert response.status_code in (403, 404)
