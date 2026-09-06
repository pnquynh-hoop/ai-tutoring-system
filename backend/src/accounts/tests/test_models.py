import pytest


@pytest.mark.django_db
class TestAccountModels:
    def test_user_group_properties(self, student, tutor):
        assert student.is_student is True
        assert student.is_tutor is False
        assert tutor.is_tutor is True
        assert tutor.is_student is False
