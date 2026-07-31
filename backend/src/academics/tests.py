import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from accounts.models import StudentProfile
from core.testing import auth_client

"""
    Danh mục dùng chung phải phản ánh đúng dữ liệu và khai báo trong model:
    khối lớp lấy từ bảng academics.Grade, học lực lấy từ TextChoices.
"""


@pytest.mark.django_db
class TestGradeCatalog:
    def test_lists_only_active_grades(self, student):
        baker.make("academics.Grade", number=10)
        baker.make("academics.Grade", number=11, is_active=False)

        response = auth_client(student).get("/api/v1/grades/")

        assert response.status_code == 200
        assert [item["name"] for item in response.data] == ["Lớp 10"]

    def test_sorted_by_number_not_alphabet(self, student):
        """Lưu chuỗi thì "Lớp 9" sẽ rơi xuống cuối, lưu số mới ra đúng thứ tự."""
        for number in [12, 9, 10]:
            baker.make("academics.Grade", number=number)

        response = auth_client(student).get("/api/v1/grades/")

        assert [item["name"] for item in response.data] == [
            "Lớp 9",
            "Lớp 10",
            "Lớp 12",
        ]

    def test_requires_authentication(self, db):
        assert APIClient().get("/api/v1/grades/").status_code == 401

    def test_is_read_only(self, student):
        response = auth_client(student).post(
            "/api/v1/grades/", {"number": 13}, format="json"
        )

        assert response.status_code == 405


@pytest.mark.django_db
class TestAcademicLevelCatalog:
    def test_returns_choices_declared_in_model(self, student):
        response = auth_client(student).get("/api/v1/users/academic-levels/")

        assert response.status_code == 200
        assert [item["value"] for item in response.data] == [
            value for value, _ in StudentProfile.AcademicLevel.choices
        ]

    def test_label_is_vietnamese_from_model(self, student):
        response = auth_client(student).get("/api/v1/users/academic-levels/")

        labels = {item["value"]: item["label"] for item in response.data}
        assert labels["POOR"] == "Yếu"
        assert labels["EXCELLENT"] == "Giỏi"

    def test_requires_authentication(self, db):
        assert APIClient().get("/api/v1/users/academic-levels/").status_code == 401
