from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from model_bakery import baker

from core.testing import make_published

"""
    Fixture dùng chung cho toàn bộ test: dựng sẵn nhóm quyền, gia sư, học sinh
    và một khóa học có chương/bài học để các app không phải lặp lại.
"""


@pytest.fixture
def student_group(db):
    return Group.objects.get_or_create(name="Student")[0]


@pytest.fixture
def tutor_group(db):
    return Group.objects.get_or_create(name="Tutor")[0]


@pytest.fixture
def make_student(student_group):
    def _make():
        user = baker.make("accounts.User")
        user.groups.add(student_group)
        return user

    return _make


@pytest.fixture
def make_tutor(tutor_group):
    def _make():
        user = baker.make("accounts.User")
        user.groups.add(tutor_group)
        return user

    return _make


@pytest.fixture
def student(make_student):
    return make_student()


@pytest.fixture
def tutor(make_tutor):
    return make_tutor()


@pytest.fixture
def course(tutor):
    return baker.make("courses.Course", tutor=tutor)


@pytest.fixture
def chapter(course):
    return make_published("courses.Chapter", course=course, order=1)


@pytest.fixture
def lesson(chapter):
    return make_published("courses.Lesson", chapter=chapter, order=1)


@pytest.fixture
def enrolled_student(course, make_student):
    """Học sinh đã ghi danh khóa học `course`."""
    user = make_student()
    baker.make("courses.Enrollment", course=course, student=user)
    return user


@pytest.fixture
def assignment(chapter):
    return make_published(
        "assignments.Assignment",
        chapter=chapter,
        due_date=timezone.now() + timedelta(days=1),
        time_limit_minutes=None,
    )
