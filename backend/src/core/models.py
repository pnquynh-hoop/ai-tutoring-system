from django.db import models


class BaseModel(models.Model):
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
