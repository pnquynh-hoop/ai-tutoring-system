import pytest
from django.utils import timezone
from model_bakery import baker

from core.testing import auth_client
from courses.models import LearningResource
from courses.serializers import (
    LearningResourceSerializer,
    TutorLearningResourceSerializer,
)

TUTOR_ONLY_FIELDS = {"is_published", "rag_status", "rag_progress"}


@pytest.fixture
def resource(lesson):
    return baker.make(
        LearningResource,
        lesson=lesson,
        title="Ngữ pháp Unit 1",
        resource_type=LearningResource.ResourceType.OTHERS,
        content="Thì hiện tại hoàn thành dùng để nói về việc đã xảy ra.",
        published_at=timezone.now(),
    )


@pytest.mark.django_db
class TestResourcePayload:
    def test_student_payload_hides_tutor_only_fields(self, resource):
        data = LearningResourceSerializer(resource).data

        assert TUTOR_ONLY_FIELDS.isdisjoint(data)

    def test_tutor_payload_keeps_tutor_only_fields(self, resource):
        data = TutorLearningResourceSerializer(resource).data

        assert TUTOR_ONLY_FIELDS.issubset(data)

    def test_student_reading_lesson_resources_gets_no_tutor_only_fields(
        self, enrolled_student, lesson, resource
    ):
        response = auth_client(enrolled_student).get(
            f"/api/v1/lessons/{lesson.id}/resources/"
        )

        assert response.status_code == 200
        assert TUTOR_ONLY_FIELDS.isdisjoint(response.data[0])
