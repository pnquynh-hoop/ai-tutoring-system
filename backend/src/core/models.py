from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    is_active = models.BooleanField("Đang hoạt động", default=True)
    created_at = models.DateTimeField("Thời điểm tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Thời điểm cập nhật", auto_now=True)

    class Meta:
        abstract = True


class RAGIndexedModel(models.Model):

    class RAGStatus(models.TextChoices):
        PENDING = "PENDING", "Chờ nạp"
        PROCESSING = "PROCESSING", "Đang nạp"
        INDEXED = "INDEXED", "Đã nạp"
        FAILED = "FAILED", "Nạp lỗi"

    rag_status = models.CharField(
        "Trạng thái RAG",
        max_length=20,
        choices=RAGStatus.choices,
        default=RAGStatus.PENDING,
    )
    rag_progress = models.PositiveIntegerField("Số chunk đã nạp", default=0)
    rag_error = models.TextField("Lý do nạp lỗi", null=True, blank=True)
    rag_indexed_at = models.DateTimeField("Thời điểm nạp xong", null=True, blank=True)

    class Meta:
        abstract = True

    def mark_rag_processing(self):
        self.rag_status = self.RAGStatus.PROCESSING
        self.rag_error = None
        self.save(update_fields=["rag_status", "rag_error", "updated_at"])

    def mark_rag_indexed(self, chunks):
        self.rag_status = self.RAGStatus.INDEXED
        self.rag_progress = chunks
        self.rag_error = None
        self.rag_indexed_at = timezone.now()
        self.save(
            update_fields=[
                "rag_status",
                "rag_progress",
                "rag_error",
                "rag_indexed_at",
                "updated_at",
            ]
        )

    def mark_rag_failed(self, error):
        self.rag_status = self.RAGStatus.FAILED
        self.rag_error = error[:2000]
        self.save(update_fields=["rag_status", "rag_error", "updated_at"])


class PublishableModel(models.Model):

    published_at = models.DateTimeField(
        "Thời điểm công khai cho học sinh", null=True, blank=True
    )

    class Meta:
        abstract = True

    @property
    def is_published(self):
        return self.published_at is not None
