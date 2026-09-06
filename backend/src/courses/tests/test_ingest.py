from types import SimpleNamespace
from unittest.mock import patch

import pytest
from model_bakery import baker

from core.permissions import IsCourseTutor, IsTutor
from core.testing import auth_client
from courses.models import LearningResource
from courses.serializers import IngestResourceSerializer


@pytest.fixture
def resource(lesson):
    return baker.make(
        LearningResource,
        lesson=lesson,
        title="Ngữ pháp Unit 1",
        resource_type=LearningResource.ResourceType.OTHERS,
        content="Thì hiện tại hoàn thành dùng để nói về việc đã xảy ra.",
        rag_status=LearningResource.RAGStatus.PENDING,
    )


@pytest.mark.django_db
class TestIngestResourceRules:
    def test_failed_resource_is_reset_to_pending(self, resource):
        resource.rag_status = LearningResource.RAGStatus.FAILED
        resource.rag_error = "Không tải được tệp từ Cloudinary."
        resource.save()

        serializer = IngestResourceSerializer(resource, data={})
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        resource.refresh_from_db()
        assert resource.rag_status == LearningResource.RAGStatus.PENDING
        assert resource.rag_error is None

    def test_resource_with_file_only_can_be_queued(self, lesson):
        pdf_resource = baker.make(
            LearningResource,
            lesson=lesson,
            title="Đề cương chương 1",
            resource_type=LearningResource.ResourceType.PDF_FILE,
            content=None,
            file_url="tutoring_center/resources/de_cuong.pdf",
            rag_status=LearningResource.RAGStatus.PENDING,
        )

        serializer = IngestResourceSerializer(pdf_resource, data={})

        assert serializer.is_valid(), serializer.errors

    def test_resource_being_ingested_is_rejected(self, resource):
        resource.rag_status = LearningResource.RAGStatus.PROCESSING
        resource.save()

        serializer = IngestResourceSerializer(resource, data={})

        assert not serializer.is_valid()
        assert "đang được nạp" in str(serializer.errors)

    def test_resource_without_content_or_file_is_rejected(self, lesson):
        video = baker.make(
            LearningResource,
            lesson=lesson,
            title="Video bài giảng",
            resource_type=LearningResource.ResourceType.VIDEO_URL,
            content=None,
            video_url="https://www.youtube.com/watch?v=abc",
        )

        serializer = IngestResourceSerializer(video, data={})

        assert not serializer.is_valid()
        assert "không có nội dung" in str(serializer.errors)


@pytest.mark.django_db
class TestIngestResourcePermissions:
    def test_student_cannot_queue_the_resource(self, enrolled_student):
        request = SimpleNamespace(user=enrolled_student)

        assert not IsTutor().has_permission(request, None)

    def test_tutor_of_another_course_cannot_queue_the_resource(
        self, tutor_group, resource
    ):
        outsider = baker.make("accounts.User")
        outsider.groups.add(tutor_group)
        request = SimpleNamespace(user=outsider)

        assert not IsCourseTutor().has_object_permission(request, None, resource)


@pytest.mark.django_db
class TestIngestResourceQueueing:
    def test_tutor_queues_the_resource(self, tutor, resource):
        with patch("courses.views.ingest_resource_task.delay") as queued:
            response = auth_client(tutor).post(
                f"/api/v1/resources/{resource.id}/ingest/"
            )

        assert response.status_code == 202
        queued.assert_called_once_with(resource.id)

    def test_broker_down_marks_the_resource_failed(self, tutor, resource):
        with patch(
            "courses.views.ingest_resource_task.delay",
            side_effect=OSError("Connection refused"),
        ):
            response = auth_client(tutor).post(
                f"/api/v1/resources/{resource.id}/ingest/"
            )

        assert response.status_code == 503
        resource.refresh_from_db()
        assert resource.rag_status == LearningResource.RAGStatus.FAILED
