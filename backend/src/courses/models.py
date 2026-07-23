from django.db import models
from core.models import BaseModel
from unidecode import unidecode
from cloudinary.models import CloudinaryField
from django.utils.text import slugify

"""
    Chứa các model Course, Enrollment, Chapter, Lesson, LearningResource, LearningProgress
"""


class Course(BaseModel):
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.PROTECT, related_name="learning_courses"
    )
    grade = models.ForeignKey(
        "academics.Grade", on_delete=models.PROTECT, related_name="courses"
    )
    tutor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="teaching_courses",
    )
    name = models.CharField("Tên khóa học", max_length=255, unique=True)
    description = models.TextField(verbose_name="Mô tả khóa học")
    students = models.ManyToManyField(
        "accounts.User",
        through="Enrollment",
        related_name="courses",
    )

    def __str__(self):
        return self.name


class Enrollment(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    student = models.ForeignKey("accounts.User", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"], name="unique_course_student"
            )
        ]

    def __str__(self):
        return f"{self.course} - {self.student}"


class Chapter(BaseModel):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="chapters"
    )
    title = models.CharField("Tiêu đề chương", max_length=255)
    order = models.IntegerField("Thứ tự chương")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "course"], name="unique_course_order"
            ),
            models.UniqueConstraint(
                fields=["title", "course"], name="unique_course_title"
            ),
        ]
    
    def __str__(self):
        return self.title


class Lesson(BaseModel):
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField("Tiêu đề bài học", max_length=255)
    order = models.IntegerField("Thứ tự bài học trong chương")
    students = models.ManyToManyField(
        "accounts.User",
        through="LessonProgress",
        related_name="lessons",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "chapter"], name="unique_chapter_order"
            ),
            models.UniqueConstraint(
                fields=["title", "chapter"], name="unique_chapter_title"
            ),
        ]

    def __str__(self):
        return self.title


def resource_upload_path(instance):
    lesson = instance.lesson
    chapter = lesson.chapter
    course = chapter.course

    course_name = slugify(unidecode(course.name))
    chapter_title = slugify(unidecode(chapter.title))
    lesson_title = slugify(unidecode(lesson.title))

    return f"tutoring_center/resources/{course_name}/{chapter_title}/{lesson_title}"


class LearningResource(BaseModel):
    class ResourceType(models.TextChoices):
        VIDEO_URL = "VIDEO_URL", "Video URL"
        PDF_FILE = "PDF_FILE", "PDF File"
        OTHERS = "OTHERS", "Khác"

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="resources"
    )
    title = models.CharField("Tên tài nguyên bài học", max_length=255)
    resource_type = models.CharField(
        "Loại tài nguyên",
        max_length=255,
        choices=ResourceType.choices,
        default=ResourceType.OTHERS,
    )
    content = models.TextField("Nội dung văn bản bài học", null=True, blank=True)
    file_url = CloudinaryField(
        "Tệp tài liệu bài học",
        folder=resource_upload_path,
        resource_type="raw",
        null=True,
        blank=True,
    )
    video_url = models.CharField(max_length=255, null=True, blank=True)
    is_rag_indexed = models.BooleanField("Đã RAG", default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["title", "lesson"], name="unique_lesson_resource_title"
            ),
        ]

    def __str__(self):
        return self.title


class LessonProgress(models.Model):
    student = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT)
    is_completed = models.BooleanField("Đánh dấu hoàn thành bài học", default=False)
    complete_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "student"], name="unique_lesson_student"
            )
        ]
    
    def __str__(self):
        return f"{self.lesson} - {self.student}"


class Comment(BaseModel):
    content = models.TextField()
    is_right = models.BooleanField(default=False)
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="comments"
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    marked_right_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_right_comments",
    )
    marked_right_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lesson} - {self.created_by}"
