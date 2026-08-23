import pytest
from model_bakery import baker

from core.testing import auth_client, make_published


@pytest.mark.django_db
class TestPublishCourseContent:
    @pytest.fixture
    def draft_chapter(self, course):
        return baker.make("courses.Chapter", course=course, order=1)

    @pytest.fixture
    def published_chapter(self, course):
        return make_published("courses.Chapter", course=course, order=2)

    def make_resource(self, lesson):
        return baker.make(
            "courses.LearningResource",
            lesson=lesson,
            resource_type="OTHERS",
            content="Nội dung tài nguyên",
        )

    def test_tutor_publishes_chapter(self, tutor, draft_chapter):
        client = auth_client(tutor)

        response = client.post(f"/api/v1/chapters/{draft_chapter.id}/publish/")

        assert response.status_code == 200
        draft_chapter.refresh_from_db()
        assert draft_chapter.is_published

    def test_publish_chapter_twice_is_rejected(self, tutor, published_chapter):
        client = auth_client(tutor)

        response = client.post(f"/api/v1/chapters/{published_chapter.id}/publish/")

        assert response.status_code == 400

    def test_lesson_is_rejected_while_chapter_is_draft(self, tutor, draft_chapter):
        lesson = baker.make("courses.Lesson", chapter=draft_chapter, order=1)
        client = auth_client(tutor)

        response = client.post(f"/api/v1/lessons/{lesson.id}/publish/")

        assert response.status_code == 400
        lesson.refresh_from_db()
        assert not lesson.is_published

    def test_lesson_is_published_after_chapter(self, tutor, published_chapter):
        lesson = baker.make("courses.Lesson", chapter=published_chapter, order=1)
        client = auth_client(tutor)

        response = client.post(f"/api/v1/lessons/{lesson.id}/publish/")

        assert response.status_code == 200
        lesson.refresh_from_db()
        assert lesson.is_published

    def test_resource_is_rejected_while_lesson_is_draft(self, tutor, published_chapter):
        draft_lesson = baker.make("courses.Lesson", chapter=published_chapter, order=1)
        resource = self.make_resource(draft_lesson)
        client = auth_client(tutor)

        response = client.post(f"/api/v1/resources/{resource.id}/publish/")

        assert response.status_code == 400
        resource.refresh_from_db()
        assert not resource.is_published

    def test_resource_is_published_after_lesson(self, tutor, published_chapter):
        published_lesson = make_published(
            "courses.Lesson", chapter=published_chapter, order=1
        )
        resource = self.make_resource(published_lesson)
        client = auth_client(tutor)

        response = client.post(f"/api/v1/resources/{resource.id}/publish/")

        assert response.status_code == 200
        resource.refresh_from_db()
        assert resource.is_published

    def test_student_cannot_publish_chapter(self, enrolled_student, draft_chapter):
        client = auth_client(enrolled_student)

        response = client.post(f"/api/v1/chapters/{draft_chapter.id}/publish/")

        assert response.status_code == 403
        draft_chapter.refresh_from_db()
        assert not draft_chapter.is_published
