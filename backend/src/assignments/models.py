from django.db import models
from core.models import BaseModel

""" 
    Chức các model Assignment, AssignQuestion, AssignSubmission, AssignAnswer
"""


class Assignment(BaseModel):
    chapter = models.OneToOneField("courses.Chapter", on_delete=models.CASCADE)
    title = models.CharField("Tiêu đề bài tập", max_length=255)
    due_date = models.DateTimeField()
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

    def __str__(self):
        return f"{self.assignment} - {self.content}"


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    content = models.TextField("Nội dung phương án")
    is_correct = models.BooleanField()

    def __str__(self):
        return f"{self.question} - {self.content}"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT)
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=3, decimal_places=1)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student"], name="unique_assignment_student"
            )
        ]

    def __str__(self):
        return f"{self.assignment} - {self.student}"


class StudentAnswer(models.Model):
    answer_text = models.TextField(null=True, blank=True)
    tutor_comment = models.TextField(null=True, blank=True)
    point = models.DecimalField(max_digits=4, decimal_places=2)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.ForeignKey(Answer, on_delete=models.SET_NULL, null=True, blank=True)
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="stu_answers"
    )

    def __str__(self):
        return f"{self.submission} - {self.question}"
