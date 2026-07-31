from datetime import timedelta

from django.db import models

from core.models import BaseModel, PublishableModel

""" 
    Chức các model Assignment, AssignQuestion, AssignSubmission, AssignAnswer
"""


class Assignment(BaseModel, PublishableModel):
    chapter = models.OneToOneField("courses.Chapter", on_delete=models.CASCADE)
    title = models.CharField("Tiêu đề bài tập", max_length=255)
    due_date = models.DateTimeField()
    time_limit_minutes = models.PositiveIntegerField(
        "Thời gian làm bài (phút)", null=True, blank=True
    )
    students = models.ManyToManyField(
        "accounts.User",
        through="Submission",
        related_name="assignments",
    )

    def __str__(self):
        return f"{self.chapter} - {self.title}"


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Trắc nghiệm"
        FILL_IN_BLANK = "FILL_IN_BLANK", "Điền khuyết"
        ESSAY = "ESSAY", "Tự luận"

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name="questions"
    )
    content = models.TextField("Nội dung câu hỏi")
    question_type = models.CharField(
        "Loại câu hỏi",
        max_length=255,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE,
    )
    explanation = models.TextField("Lời giải chi tiết")
    order = models.PositiveIntegerField("Thứ tự câu hỏi", null=True, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "order"],
                name="unique_assignment_question_order",
            )
        ]
        indexes = [models.Index(fields=["assignment", "order"])]

    def __str__(self):
        return f"{self.assignment} - {self.content}"


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    content = models.TextField("Nội dung phương án")
    is_correct = models.BooleanField()

    def __str__(self):
        return f"{self.question} - {self.content}"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT)
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    # started_at được ghi khi học sinh bắt đầu làm bài, dùng để ép time_limit_minutes.
    started_at = models.DateTimeField(
        "Thời điểm bắt đầu làm bài", null=True, blank=True
    )
    # submitted_at chỉ có giá trị khi bài đã nộp; đang làm dở thì để null.
    submitted_at = models.DateTimeField("Thời điểm nộp bài", null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [models.Index(fields=["assignment", "student"])]

    def __str__(self):
        return f"{self.assignment} - {self.student}"

    @property
    def deadline(self):
        """Thời điểm hết giờ làm bài của lượt làm này (None nếu không giới hạn)."""
        limit = self.assignment.time_limit_minutes
        if not limit or not self.started_at:
            return None
        return self.started_at + timedelta(minutes=limit)


class StudentAnswer(models.Model):
    answer_text = models.TextField(null=True, blank=True)
    tutor_comment = models.TextField(null=True, blank=True)
    point = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.ForeignKey(Answer, on_delete=models.SET_NULL, null=True, blank=True)
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="stu_answers"
    )

    def __str__(self):
        return f"{self.submission} - {self.question}"
