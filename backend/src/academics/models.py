import os

from unidecode import unidecode
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from core.models import BaseModel, RAGIndexedModel
from cloudinary.models import CloudinaryField

"""
    Chứa model Subject, Grade, Topic, TutorSubject
"""


class Subject(BaseModel):
    name = models.CharField("Tên môn học", max_length=255, unique=True)
    description = models.TextField(verbose_name="Mô tả môn học")

    def __str__(self):
        return self.name


class Grade(BaseModel):
    number = models.PositiveSmallIntegerField("Khối lớp", unique=True)

    class Meta:
        ordering = ["number"]

    @property
    def name(self) -> str:
        return f"Lớp {self.number}"

    def __str__(self):
        return self.name


def _material_folder(instance) -> str:
    grade_name = unidecode(instance.grade.name).replace(" ", "_")
    subject_name = unidecode(instance.subject.name).replace(" ", "_")

    return f"{grade_name}/{subject_name}"


def material_upload_path(instance):
    return f"tutoring_center/materials/{_material_folder(instance)}"


def material_local_path(instance, filename) -> str:
    """Thư mục con trong RAG_DATA_DIR, nằm ngoài glob nạp sách giáo khoa."""
    return f"materials/{_material_folder(instance)}/{filename}"


class RAGDataStorage(FileSystemStorage):
    """Đọc RAG_DATA_DIR lúc lưu tệp thay vì chốt cứng lúc khai báo field."""

    @property
    def base_location(self):
        return settings.RAG_DATA_DIR

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def rag_data_storage() -> RAGDataStorage:
    return RAGDataStorage()


class Material(BaseModel, RAGIndexedModel):
    """Tài liệu chung của trung tâm.

    Tệp tối đa 10MB lưu trên Cloudinary, tệp lớn hơn lưu cục bộ trong
    RAG_DATA_DIR. Mỗi bản ghi chỉ dùng một trong hai.
    """

    name = models.CharField(max_length=255)
    file_url = CloudinaryField(
        "Tệp trên Cloudinary", folder=material_upload_path, null=True, blank=True
    )
    local_file = models.FileField(
        "Tệp lưu cục bộ",
        upload_to=material_local_path,
        storage=rag_data_storage,
        max_length=500,
        null=True,
        blank=True,
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="materials"
    )
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="materials")

    def __str__(self):
        return self.name

    @property
    def is_local(self) -> bool:
        return bool(self.local_file)

    def clean(self):
        super().clean()
        if bool(self.file_url) == bool(self.local_file):
            raise ValidationError(
                "Tài liệu phải có đúng một nguồn tệp: Cloudinary hoặc cục bộ."
            )
