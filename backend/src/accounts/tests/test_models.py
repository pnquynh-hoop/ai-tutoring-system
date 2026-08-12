import pytest
from django.contrib.auth.models import Group
from model_bakery import baker


@pytest.mark.django_db
class TestAccountModels:

    @pytest.fixture
    def student_group(self):
        return Group.objects.create(name="Student")

    @pytest.fixture
    def tutor_group(self):
        return Group.objects.create(name="Tutor")

    @pytest.fixture
    def student(self, student_group):
        user = baker.make("accounts.User")
        user.groups.add(student_group)
        return user

    @pytest.fixture
    def tutor(self, tutor_group):
        user = baker.make("accounts.User")
        user.groups.add(tutor_group)
        return user

    def test_user_group_properties(self, student, tutor):
        assert student.is_student is True
        assert student.is_tutor is False
        assert tutor.is_tutor is True
        assert tutor.is_student is False
