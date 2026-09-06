import pytest

from core.testing import auth_client


@pytest.mark.django_db
class TestCourseDetailAccess:
    def test_enrolled_student_reads_the_course(self, enrolled_student, course):
        response = auth_client(enrolled_student).get(f"/api/v1/courses/{course.id}/")

        assert response.status_code == 200

    def test_owning_tutor_cannot_read_the_course_detail(self, tutor, course):
        response = auth_client(tutor).get(f"/api/v1/courses/{course.id}/")

        assert response.status_code == 403
