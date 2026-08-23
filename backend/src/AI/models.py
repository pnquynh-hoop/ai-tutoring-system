from django.db import models



class Report(models.Model):
    class ReportStatus(models.TextChoices):
        REPORTED = "REPORTED", "Đã báo cáo"
        REVIEWING = "REVIEWING", "Đang xem xét"
        SOLVED = "SOLVED", "Đã xử lý"

    question = models.ForeignKey("assignments.Question", on_delete=models.CASCADE)
    reporter = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="reports"
    )
    note = models.TextField()
    status = models.CharField(
        "", max_length=255, choices=ReportStatus.choices, default=ReportStatus.REPORTED
    )
    reported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.question} - {self.reporter}"
