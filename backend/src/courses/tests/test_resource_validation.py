from types import SimpleNamespace

import pytest
from model_bakery import baker

from courses.models import LearningResource
from courses.serializers import ResourceSerializer


def tutor_context(lesson):
    return {"request": SimpleNamespace(user=lesson.chapter.course.tutor)}


@pytest.fixture
def pdf_resource(lesson):
    return baker.make(
        LearningResource,
        lesson=lesson,
        title="Đề cương chương 1",
        resource_type=LearningResource.ResourceType.PDF_FILE,
        content=None,
        file_url="tutoring_center/resources/de_cuong.pdf",
    )


@pytest.mark.django_db
class TestResourceValidation:
    def test_pdf_without_file_is_rejected(self, lesson):
        serializer = ResourceSerializer(
            data={
                "lesson": lesson.id,
                "title": "Đề cương",
                "resource_type": LearningResource.ResourceType.PDF_FILE,
            },
            context=tutor_context(lesson),
        )

        assert not serializer.is_valid()
        assert "phải có tệp tài liệu" in str(serializer.errors)

    def test_renaming_a_pdf_keeps_the_stored_file(self, pdf_resource):
        serializer = ResourceSerializer(
            pdf_resource, data={"title": "Đề cương bản mới"}, partial=True
        )

        assert serializer.is_valid(), serializer.errors

    def test_switching_resource_type_is_rejected(self, pdf_resource):
        serializer = ResourceSerializer(
            pdf_resource,
            data={"resource_type": LearningResource.ResourceType.VIDEO_URL},
            partial=True,
        )

        assert not serializer.is_valid()
        assert "Không được đổi loại tài nguyên" in str(serializer.errors)

    def test_video_without_link_is_rejected(self, lesson):
        serializer = ResourceSerializer(
            data={
                "lesson": lesson.id,
                "title": "Video bài giảng",
                "resource_type": LearningResource.ResourceType.VIDEO_URL,
            },
            context=tutor_context(lesson),
        )

        assert not serializer.is_valid()
        assert "phải có đường dẫn video" in str(serializer.errors)
