import pytest
from model_bakery import baker
from core.testing import auth_client
from rest_framework.test import APIClient


@pytest.fixture
def student_with_profile(student):
    baker.make(
        "accounts.StudentProfile",
        user=student,
        learning_goals="Đạt 8 điểm",
        academic_level="AVERAGE",
    )
    return student


@pytest.mark.django_db
class TestMeEndpoint:
    def test_returns_profile_of_current_user(self, student_with_profile):
        response = auth_client(student_with_profile).get("/api/v1/users/me/")

        assert response.status_code == 200
        assert response.data["id"] == student_with_profile.pk
        assert response.data["role"] == "Student"
        assert response.data["student_profile"]["learning_goals"] == "Đạt 8 điểm"

    def test_anonymous_is_blocked(self):
        assert APIClient().get("/api/v1/users/me/").status_code == 401

    def test_update_own_basic_info(self, student):
        response = auth_client(student).patch(
            "/api/v1/users/me/",
            {"first_name": "Quỳnh", "last_name": "Hồ", "phone": "0900000001"},
            format="json",
        )

        assert response.status_code == 200
        student.refresh_from_db()
        assert student.first_name == "Quỳnh"
        assert student.full_name == "Hồ Quỳnh"

    def test_update_student_profile(self, student_with_profile):
        response = auth_client(student_with_profile).patch(
            "/api/v1/users/me/",
            {
                "student_profile": {
                    "learning_goals": "Thi đại học",
                    "academic_level": "GOOD",
                }
            },
            format="json",
        )

        assert response.status_code == 200
        student_with_profile.studentprofile.refresh_from_db()
        assert student_with_profile.studentprofile.learning_goals == "Thi đại học"
        assert student_with_profile.studentprofile.academic_level == "GOOD"

    def test_tutor_profile_is_not_editable(self, tutor):
        baker.make("accounts.TutorProfile", user=tutor, experience_years=1)

        response = auth_client(tutor).patch(
            "/api/v1/users/me/",
            {"tutor_profile": {"bio": "10 năm dạy Toán", "experience_years": 10}},
            format="json",
        )

        assert response.status_code == 200
        tutor.tutorprofile.refresh_from_db()
        assert tutor.tutorprofile.experience_years == 1
        assert tutor.tutorprofile.bio != "10 năm dạy Toán"

    def test_is_verified_is_read_only(self, tutor):
        baker.make("accounts.TutorProfile", user=tutor, is_verified=False)

        auth_client(tutor).patch(
            "/api/v1/users/me/",
            {"tutor_profile": {"bio": "x", "is_verified": True}},
            format="json",
        )

        tutor.tutorprofile.refresh_from_db()
        assert tutor.tutorprofile.is_verified is False

    def test_student_can_update_grade_level(self, student_with_profile):
        grade = baker.make("academics.Grade", number=12)

        response = auth_client(student_with_profile).patch(
            "/api/v1/users/me/",
            {"student_profile": {"grade_level": grade.pk}},
            format="json",
        )

        assert response.status_code == 200
        student_with_profile.studentprofile.refresh_from_db()
        assert student_with_profile.studentprofile.grade_level_id == grade.pk
        assert response.data["student_profile"]["grade_name"] == "Lớp 12"

    def test_unknown_grade_is_rejected(self, student_with_profile):
        response = auth_client(student_with_profile).patch(
            "/api/v1/users/me/",
            {"student_profile": {"grade_level": 999999}},
            format="json",
        )

        assert response.status_code == 400

    def test_invalid_academic_level_is_rejected(self, student_with_profile):
        response = auth_client(student_with_profile).patch(
            "/api/v1/users/me/",
            {"student_profile": {"academic_level": "SIEU_GIOI"}},
            format="json",
        )

        assert response.status_code == 400

    def test_duplicate_email_is_rejected(self, student, make_student):
        other = make_student()
        response = auth_client(student).patch(
            "/api/v1/users/me/", {"email": other.email}, format="json"
        )

        assert response.status_code == 400
        assert "email" in response.data


@pytest.mark.django_db
class TestChangePassword:
    def test_change_password_success(self, student):
        student.set_password("MatKhauCu@123")
        student.save()

        response = auth_client(student).post(
            "/api/v1/users/change-password/",
            {
                "old_password": "MatKhauCu@123",
                "new_password": "MatKhauMoi@456",
                "confirm_password": "MatKhauMoi@456",
            },
            format="json",
        )

        assert response.status_code == 200
        student.refresh_from_db()
        assert student.check_password("MatKhauMoi@456")

    def test_wrong_old_password(self, student):
        student.set_password("MatKhauCu@123")
        student.save()

        response = auth_client(student).post(
            "/api/v1/users/change-password/",
            {
                "old_password": "MatKhauSai@123",
                "new_password": "MatKhauMoi@456",
                "confirm_password": "MatKhauMoi@456",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "old_password" in response.data

    def test_confirm_password_mismatch(self, student):
        student.set_password("MatKhauCu@123")
        student.save()

        response = auth_client(student).post(
            "/api/v1/users/change-password/",
            {
                "old_password": "MatKhauCu@123",
                "new_password": "MatKhauMoi@456",
                "confirm_password": "KhacRoi@789",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "confirm_password" in response.data

    def test_weak_password_is_rejected(self, student):
        student.set_password("MatKhauCu@123")
        student.save()

        response = auth_client(student).post(
            "/api/v1/users/change-password/",
            {
                "old_password": "MatKhauCu@123",
                "new_password": "123456",
                "confirm_password": "123456",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "new_password" in response.data
