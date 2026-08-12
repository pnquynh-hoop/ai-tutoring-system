from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RAGIndexedModel(models.Model):
    """Theo dõi tiến trình nạp tài liệu vào vector store."""

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

    def mark_rag_indexed(self, chunks: int):
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

    def mark_rag_failed(self, error: str):
        self.rag_status = self.RAGStatus.FAILED
        self.rag_error = error[:2000]
        self.save(update_fields=["rag_status", "rag_error", "updated_at"])


class PublishableModel(models.Model):
    """Nội dung học liệu do gia sư soạn: để trống là bản nháp, có giá trị là đã công khai."""

    published_at = models.DateTimeField(
        "Thời điểm công khai cho học sinh", null=True, blank=True
    )

    class Meta:
        abstract = True

    @property
    def is_published(self) -> bool:
        return self.published_at is not None
