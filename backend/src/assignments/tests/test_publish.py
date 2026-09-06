from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone
from model_bakery import baker

from assignments.serializers import PublishAssignmentSerializer
from core.permissions import IsTutor
from courses.models import Chapter


@pytest.mark.django_db
class TestPublishAssignment:
    def make_published_chapter(self, course):
        return Chapter.objects.create(
            course=course,
            title="Chương 1",
            order=1,
            published_at=timezone.now(),
        )

    def make_assignment(self, chapter):
        return baker.make(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=None,
        )

    def make_question(self, assignment, order, point):
        return baker.make(
            "assignments.Question",
            assignment=assignment,
            order=order,
            point=point,
        )

    def test_assignment_is_rejected_while_chapter_is_draft(self, course):
        draft_chapter = baker.make("courses.Chapter", course=course, order=1)
        assignment = self.make_assignment(draft_chapter)

        serializer = PublishAssignmentSerializer(assignment, data={})

        assert not serializer.is_valid()
        assert "Phải công khai chương" in str(serializer.errors)

    def test_assignment_is_published_after_chapter(self, course):
        published_chapter = self.make_published_chapter(course)
        assignment = self.make_assignment(published_chapter)
        self.make_question(assignment, order=1, point=Decimal("10"))

        serializer = PublishAssignmentSerializer(assignment, data={})
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assignment.refresh_from_db()
        assert assignment.is_published

    def test_assignment_is_rejected_when_a_question_has_no_point(self, course):
        published_chapter = self.make_published_chapter(course)
        assignment = self.make_assignment(published_chapter)
        self.make_question(assignment, order=1, point=Decimal("10"))
        self.make_question(assignment, order=2, point=None)

        serializer = PublishAssignmentSerializer(assignment, data={})

        assert not serializer.is_valid()
        assert "chưa đặt điểm" in str(serializer.errors)

    def test_assignment_is_rejected_when_points_do_not_reach_ten(self, course):
        published_chapter = self.make_published_chapter(course)
        assignment = self.make_assignment(published_chapter)
        self.make_question(assignment, order=1, point=Decimal("4"))
        self.make_question(assignment, order=2, point=Decimal("4"))

        serializer = PublishAssignmentSerializer(assignment, data={})

        assert not serializer.is_valid()
        assert "Tổng điểm" in str(serializer.errors)

    def test_assignment_without_question_is_rejected(self, course):
        published_chapter = self.make_published_chapter(course)
        assignment = self.make_assignment(published_chapter)

        serializer = PublishAssignmentSerializer(assignment, data={})

        assert not serializer.is_valid()
        assert "chưa có câu hỏi" in str(serializer.errors)

    def test_published_assignment_cannot_be_published_again(self, course):
        published_chapter = self.make_published_chapter(course)
        assignment = self.make_assignment(published_chapter)
        self.make_question(assignment, order=1, point=Decimal("10"))
        assignment.published_at = timezone.now()
        assignment.save(update_fields=["published_at"])

        serializer = PublishAssignmentSerializer(assignment, data={})

        assert not serializer.is_valid()
        assert "đã được công khai" in str(serializer.errors)

    def test_student_cannot_publish_assignment(self, enrolled_student):
        request = SimpleNamespace(user=enrolled_student)

        assert not IsTutor().has_permission(request, None)
