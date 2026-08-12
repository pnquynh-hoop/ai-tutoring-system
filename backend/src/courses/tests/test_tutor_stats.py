from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker

from core.testing import auth_client

from courses.services import get_course_tutor_stats, mark_lesson_completed


@pytest.fixture
def lessons(chapter):
    return [
        baker.make("courses.Lesson", chapter=chapter, order=index)
        for index in range(1, 5)
    ]


@pytest.mark.django_db
class TestCourseTutorStats:
    def test_counts_students_and_progress(self, course, lessons, enrolled_student):
        mark_lesson_completed(enrolled_student, lessons[0])

        stats = get_course_tutor_stats(course)

        assert stats["total_students"] == 1
        assert stats["total_lessons"] == 4
        assert stats["students"][0]["completed_lessons"] == 1
        assert stats["students"][0]["progress"] == 25.0
        assert stats["students"][0]["average_score"] is None

    def test_inactive_enrollment_is_excluded(self, course, make_student):
        baker.make(
            "courses.Enrollment",
            course=course,
            student=make_student(),
            is_active=False,
        )

        assert get_course_tutor_stats(course)["total_students"] == 0

    def test_average_score_only_counts_submitted(
        self, course, chapter, enrolled_student
    ):
        assignment = baker.make(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=Decimal("8.0"),
            submitted_at=timezone.now(),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=Decimal("2.0"),
            submitted_at=None,
        )

        stats = get_course_tutor_stats(course)

        assert float(stats["students"][0]["average_score"]) == 8.0

    def test_assignment_stats(self, course, chapter, enrolled_student, make_student):
        assignment = baker.make(
            "assignments.Assignment",
            chapter=chapter,
            title="Kiểm tra",
            due_date=timezone.now() + timedelta(days=1),
        )
        other = make_student()
        baker.make("courses.Enrollment", course=course, student=other)

        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=Decimal("9.0"),
            submitted_at=timezone.now(),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=other,
            score=None,
            submitted_at=timezone.now(),
        )

        stat = get_course_tutor_stats(course)["assignments"][0]

        assert stat["title"] == "Kiểm tra"
        assert stat["chapter_title"] == chapter.title
        assert stat["submitted_count"] == 2
        assert stat["graded_count"] == 1
        assert stat["pending_count"] == 1
        assert float(stat["average_score"]) == 9.0

    def test_course_without_data(self, course):
        stats = get_course_tutor_stats(course)

        assert stats == {
            "total_students": 0,
            "total_lessons": 0,
            "students": [],
            "assignments": [],
        }


@pytest.mark.django_db
class TestCourseStatsApi:
    def test_course_tutor_can_read_stats(self, course, lessons, enrolled_student):
        response = auth_client(course.tutor).get(f"/api/v1/courses/{course.pk}/stats/")

        assert response.status_code == 200
        assert response.data["total_students"] == 1
        assert len(response.data["students"]) == 1

    def test_other_tutor_cannot_read_stats(self, course, make_tutor):
        response = auth_client(make_tutor()).get(f"/api/v1/courses/{course.pk}/stats/")

        assert response.status_code in (403, 404)

    def test_student_cannot_read_stats(self, course, enrolled_student):
        response = auth_client(enrolled_student).get(
            f"/api/v1/courses/{course.pk}/stats/"
        )

        # Học sinh đã ghi danh vẫn là thành viên khóa học nhưng không phải gia sư.
        assert response.status_code == 403
