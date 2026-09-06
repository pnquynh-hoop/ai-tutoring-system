from django.db import models
from core.models import BaseModel, PublishableModel, RAGIndexedModel
from unidecode import unidecode
from cloudinary.models import CloudinaryField
from django.utils.text import slugify



class Course(BaseModel):
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="learning_courses",
        verbose_name="Môn học",
    )
    grade = models.ForeignKey(
        "academics.Grade",
        on_delete=models.PROTECT,
        related_name="courses",
        verbose_name="Khối lớp",
    )
    tutor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="teaching_courses",
        verbose_name="Gia sư phụ trách",
    )
    name = models.CharField("Tên khóa học", max_length=255, unique=True)
    description = models.TextField(verbose_name="Mô tả khóa học")
    students = models.ManyToManyField(
        "accounts.User",
        through="Enrollment",
        related_name="courses",
        verbose_name="Học sinh theo học",
    )

    class Meta:
        verbose_name = "Khóa học"
        verbose_name_plural = "Khóa học"

    def __str__(self):
        return self.name


class Enrollment(BaseModel):
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, verbose_name="Khóa học"
    )
    student = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, verbose_name="Học sinh"
    )

    class Meta:
        verbose_name = "Lượt ghi danh"
        verbose_name_plural = "Lượt ghi danh"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"], name="unique_course_student"
            )
        ]

    def __str__(self):
        return f"{self.course} - {self.student}"


class Chapter(BaseModel, PublishableModel):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="chapters",
        verbose_name="Khóa học",
    )
    title = models.CharField("Tiêu đề chương", max_length=255)
    order = models.IntegerField("Thứ tự chương")

    class Meta:
        ordering = ["order"]
        verbose_name = "Chương"
        verbose_name_plural = "Chương"
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


class Lesson(BaseModel, PublishableModel):
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Chương",
    )
    title = models.CharField("Tiêu đề bài học", max_length=255)
    order = models.IntegerField("Thứ tự bài học trong chương")
    students = models.ManyToManyField(
        "accounts.User",
        through="LessonProgress",
        related_name="lessons",
        verbose_name="Học sinh đã học",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Bài học"
        verbose_name_plural = "Bài học"
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


class LearningResource(BaseModel, PublishableModel, RAGIndexedModel):
    class ResourceType(models.TextChoices):
        VIDEO_URL = "VIDEO_URL", "Video URL"
        PDF_FILE = "PDF_FILE", "PDF File"
        OTHERS = "OTHERS", "Khác"

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="resources",
        verbose_name="Bài học",
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
    video_url = models.CharField(
        "Đường dẫn video", max_length=255, null=True, blank=True
    )

    class Meta:
        verbose_name = "Tài nguyên bài học"
        verbose_name_plural = "Tài nguyên bài học"
        constraints = [
            models.UniqueConstraint(
                fields=["title", "lesson"], name="unique_lesson_resource_title"
            ),
        ]

    def __str__(self):
        return self.title


class LessonProgress(models.Model):
    student = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, verbose_name="Học sinh"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.PROTECT, verbose_name="Bài học"
    )
    is_completed = models.BooleanField("Đánh dấu hoàn thành bài học", default=False)
    complete_at = models.DateTimeField("Thời điểm hoàn thành", null=True, blank=True)

    class Meta:
        verbose_name = "Tiến độ học bài"
        verbose_name_plural = "Tiến độ học bài"
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "student"], name="unique_lesson_student"
            )
        ]

    def __str__(self):
        return f"{self.lesson} - {self.student}"


class Comment(BaseModel):
    content = models.TextField("Nội dung bình luận")
    is_right = models.BooleanField("Được đánh dấu là đúng", default=False)
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Bài học",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Người viết",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Bình luận cha",
    )
    marked_right_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_right_comments",
        verbose_name="Người đánh dấu đúng",
    )
    marked_right_at = models.DateTimeField(
        "Thời điểm đánh dấu đúng",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận"

    def __str__(self):
        return f"{self.lesson} - {self.created_by}"
