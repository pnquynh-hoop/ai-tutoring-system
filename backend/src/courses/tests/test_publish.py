from types import SimpleNamespace

import pytest
from django.utils import timezone
from model_bakery import baker

from core.permissions import IsTutor
from courses.models import Chapter, Lesson
from courses.serializers import (
    PublishChapterSerializer,
    PublishLessonSerializer,
    PublishResourceSerializer,
)


@pytest.mark.django_db
class TestPublishCourseContent:
    @pytest.fixture
    def draft_chapter(self, course):
        return baker.make("courses.Chapter", course=course, order=1)

    @pytest.fixture
    def published_chapter(self, course):
        return Chapter.objects.create(
            course=course,
            title="Chương 2",
            order=2,
            published_at=timezone.now(),
        )

    def make_published_lesson(self, chapter):
        return Lesson.objects.create(
            chapter=chapter,
            title="Bài 1",
            order=1,
            published_at=timezone.now(),
        )

    def make_resource(self, lesson):
        return baker.make(
            "courses.LearningResource",
            lesson=lesson,
            resource_type="OTHERS",
            content="Nội dung tài nguyên",
        )

    def test_tutor_publishes_chapter(self, draft_chapter):
        serializer = PublishChapterSerializer(draft_chapter, data={})
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        draft_chapter.refresh_from_db()
        assert draft_chapter.is_published

    def test_publish_chapter_twice_is_rejected(self, published_chapter):
        serializer = PublishChapterSerializer(published_chapter, data={})

        assert not serializer.is_valid()
        assert "đã được công khai" in str(serializer.errors)

    def test_lesson_is_rejected_while_chapter_is_draft(self, draft_chapter):
        lesson = baker.make("courses.Lesson", chapter=draft_chapter, order=1)

        serializer = PublishLessonSerializer(lesson, data={})

        assert not serializer.is_valid()
        assert "Phải công khai chương" in str(serializer.errors)

    def test_lesson_is_published_after_chapter(self, published_chapter):
        lesson = baker.make("courses.Lesson", chapter=published_chapter, order=1)

        serializer = PublishLessonSerializer(lesson, data={})
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        lesson.refresh_from_db()
        assert lesson.is_published

    def test_publish_lesson_twice_is_rejected(self, published_chapter):
        published_lesson = self.make_published_lesson(published_chapter)

        serializer = PublishLessonSerializer(published_lesson, data={})

        assert not serializer.is_valid()
        assert "đã được công khai" in str(serializer.errors)

    def test_resource_is_rejected_while_lesson_is_draft(self, published_chapter):
        draft_lesson = baker.make("courses.Lesson", chapter=published_chapter, order=1)
        resource = self.make_resource(draft_lesson)

        serializer = PublishResourceSerializer(resource, data={})

        assert not serializer.is_valid()
        assert "Phải công khai bài học" in str(serializer.errors)

    def test_resource_is_published_after_lesson(self, published_chapter):
        published_lesson = self.make_published_lesson(published_chapter)
        resource = self.make_resource(published_lesson)

        serializer = PublishResourceSerializer(resource, data={})
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        resource.refresh_from_db()
        assert resource.is_published

    def test_publish_resource_twice_is_rejected(self, published_chapter):
        published_lesson = self.make_published_lesson(published_chapter)
        resource = self.make_resource(published_lesson)
        resource.published_at = timezone.now()
        resource.save(update_fields=["published_at"])

        serializer = PublishResourceSerializer(resource, data={})

        assert not serializer.is_valid()
        assert "đã được công khai" in str(serializer.errors)

    def test_student_cannot_publish_chapter(self, enrolled_student):
        request = SimpleNamespace(user=enrolled_student)

        assert not IsTutor().has_permission(request, None)
