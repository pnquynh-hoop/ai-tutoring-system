from django.db import migrations
from django.utils import timezone


def publish_complete_chapters(apps, schema_editor):
    """Công khai những chương đã soạn xong: có bài học và bài tập đã có câu hỏi."""
    Chapter = apps.get_model("courses", "Chapter")
    Lesson = apps.get_model("courses", "Lesson")
    LearningResource = apps.get_model("courses", "LearningResource")
    Assignment = apps.get_model("assignments", "Assignment")
    Question = apps.get_model("assignments", "Question")

    ready_ids = [
        chapter.id
        for chapter in Chapter.objects.all()
        if Lesson.objects.filter(chapter=chapter).exists()
        and Question.objects.filter(assignment__chapter=chapter).exists()
    ]

    if not ready_ids:
        return

    now = timezone.now()
    Chapter.objects.filter(id__in=ready_ids).update(published_at=now)
    Lesson.objects.filter(chapter_id__in=ready_ids).update(published_at=now)
    LearningResource.objects.filter(lesson__chapter_id__in=ready_ids).update(
        published_at=now
    )
    Assignment.objects.filter(chapter_id__in=ready_ids).update(published_at=now)


def unpublish_all(apps, schema_editor):
    for app_label, model_name in (
        ("courses", "Chapter"),
        ("courses", "Lesson"),
        ("courses", "LearningResource"),
        ("assignments", "Assignment"),
    ):
        apps.get_model(app_label, model_name).objects.update(published_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0006_chapter_published_at_learningresource_published_at_and_more"),
        ("assignments", "0007_assignment_published_at"),
    ]

    operations = [
        migrations.RunPython(publish_complete_chapters, unpublish_all),
    ]
