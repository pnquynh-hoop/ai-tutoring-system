from django.db import models


class Conversation(models.Model):
    student = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Học sinh",
    )
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, verbose_name="Khóa học"
    )
    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Bài học",
    )
    question = models.TextField("Câu hỏi của học sinh")
    answer = models.TextField("Câu trả lời của trợ lý AI")
    sources = models.JSONField("Nguồn tài liệu", default=list, blank=True)
    is_grounded = models.BooleanField("Trả lời dựa trên tài liệu khóa học")
    asked_at = models.DateTimeField("Thời điểm hỏi", auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "Lượt hỏi trợ lý AI"
        verbose_name_plural = "Lượt hỏi trợ lý AI"
        indexes = [models.Index(fields=["student", "course"])]

    def __str__(self):
        return f"{self.student} - {self.question[:50]}"
