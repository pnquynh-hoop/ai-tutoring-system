import pytest
from model_bakery import baker

from core.testing import auth_client
from courses.models import Course


@pytest.mark.django_db
class TestCourseIsReadOnly:
    """Khóa học do admin tạo trong trang quản trị, API không mở đường tạo mới."""

    def payload(self):
        return {
            "name": "Toán 12 nâng cao",
            "description": "Mô tả khóa học",
            "subject": baker.make("academics.Subject").pk,
            "grade": baker.make("academics.Grade").pk,
        }

    def test_gia_su_khong_tao_duoc_khoa_hoc(self, tutor):
        response = auth_client(tutor).post(
            "/api/v1/courses/", self.payload(), format="json"
        )

        assert response.status_code == 405
        assert not Course.objects.filter(name="Toán 12 nâng cao").exists()

    def test_hoc_sinh_khong_tao_duoc_khoa_hoc(self, student):
        response = auth_client(student).post(
            "/api/v1/courses/", self.payload(), format="json"
        )

        assert response.status_code in (403, 405)
        assert not Course.objects.filter(name="Toán 12 nâng cao").exists()

    def test_van_doc_duoc_danh_sach(self, enrolled_student):
        response = auth_client(enrolled_student).get("/api/v1/courses/")

        assert response.status_code == 200
