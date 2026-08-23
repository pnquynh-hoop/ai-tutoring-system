from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from core.testing import auth_client, make_published


@pytest.mark.django_db
class TestPublishAssignment:
    def make_assignment(self, chapter):
        return baker.make(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
            time_limit_minutes=None,
        )

    def test_assignment_is_rejected_while_chapter_is_draft(self, tutor, course):
        draft_chapter = baker.make("courses.Chapter", course=course, order=1)
        assignment = self.make_assignment(draft_chapter)
        client = auth_client(tutor)

        response = client.post(f"/api/v1/assignments/{assignment.id}/publish/")

        assert response.status_code == 400
        assignment.refresh_from_db()
        assert not assignment.is_published

    def test_assignment_is_published_after_chapter(self, tutor, course):
        published_chapter = make_published("courses.Chapter", course=course, order=1)
        assignment = self.make_assignment(published_chapter)
        client = auth_client(tutor)

        response = client.post(f"/api/v1/assignments/{assignment.id}/publish/")

        assert response.status_code == 200
        assignment.refresh_from_db()
        assert assignment.is_published

    def test_student_cannot_publish_assignment(self, enrolled_student, course):
        published_chapter = make_published("courses.Chapter", course=course, order=1)
        assignment = self.make_assignment(published_chapter)
        client = auth_client(enrolled_student)

        response = client.post(f"/api/v1/assignments/{assignment.id}/publish/")

        assert response.status_code == 403
        assignment.refresh_from_db()
        assert not assignment.is_published
