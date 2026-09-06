from types import SimpleNamespace

import pytest
from model_bakery import baker

from courses.models import Comment
from courses.serializers import CommentSerializer


@pytest.fixture
def comment(lesson, student):
    return baker.make(
        Comment, lesson=lesson, created_by=student, content="Em chưa hiểu chỗ này"
    )


def build_reply(student, lesson, parent):
    return CommentSerializer(
        data={"content": "Chỗ đó em xem lại ví dụ 2 nhé", "parent": parent.id, "lesson": lesson.id},
        context={"request": SimpleNamespace(user=student)},
    )


@pytest.mark.django_db
class TestCommentPayload:
    def test_payload_hides_lesson_and_active_flag(self, comment):
        data = CommentSerializer(comment).data

        assert "lesson" not in data
        assert "is_active" not in data

    def test_reply_from_another_lesson_is_rejected(self, chapter, lesson, comment, student):
        other_lesson = baker.make("courses.Lesson", chapter=chapter, order=2)

        serializer = build_reply(student, other_lesson, comment)

        assert not serializer.is_valid()
        assert "cùng một bài học" in str(serializer.errors)

    def test_reply_in_the_same_lesson_is_accepted(self, lesson, comment, student):
        serializer = build_reply(student, lesson, comment)

        assert serializer.is_valid(), serializer.errors
