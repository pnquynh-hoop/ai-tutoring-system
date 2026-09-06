from datetime import timedelta
import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from model_bakery import baker
from assignments.models import Assignment
from courses.models import Chapter, Lesson


@pytest.fixture
def student_group(db):
    group, _ = Group.objects.get_or_create(name="Student")
    return group


@pytest.fixture
def tutor_group(db):
    group, _ = Group.objects.get_or_create(name="Tutor")
    return group


@pytest.fixture
def student(student_group):
    user = baker.make("accounts.User")
    user.groups.add(student_group)
    return user


@pytest.fixture
def tutor(tutor_group):
    user = baker.make("accounts.User")
    user.groups.add(tutor_group)
    return user


@pytest.fixture
def course(tutor):
    return baker.make("courses.Course", tutor=tutor)


@pytest.fixture
def chapter(course):
    return baker.make(
        "courses.Chapter",
        course=course,
        title="Chương 1",
        order=1,
        published_at=timezone.now(),
    )


@pytest.fixture
def lesson(chapter):
    return baker.make(
        "courses.Lesson",
        chapter=chapter,
        title="Bài 1",
        order=1,
        published_at=timezone.now(),
    )


@pytest.fixture
def enrolled_student(student, course):
    baker.make(
        "courses.Enrollment",
        course=course,
        student=student,
    )
    return student


@pytest.fixture
def assignment(chapter):
    return baker.make(
        "assignments.Assignment",
        chapter=chapter,
        title="Bài tập chương 1",
        due_date=timezone.now() + timedelta(days=1),
        time_limit_minutes=None,
        published_at=timezone.now(),
    )
