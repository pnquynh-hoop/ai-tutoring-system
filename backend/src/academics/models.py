from unidecode import unidecode
from django.db import models
from core.models import BaseModel, RAGIndexedModel
from cloudinary.models import CloudinaryField



class Subject(BaseModel):
    name = models.CharField("Tên môn học", max_length=255, unique=True)
    description = models.TextField(verbose_name="Mô tả môn học")

    class Meta:
        verbose_name = "Môn học"
        verbose_name_plural = "Môn học"

    def __str__(self):
        return self.name


class Grade(BaseModel):
    number = models.PositiveSmallIntegerField("Khối lớp", unique=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "Khối lớp"
        verbose_name_plural = "Khối lớp"

    @property
    def name(self):
        return f"Lớp {self.number}"

    def __str__(self):
        return self.name


def material_folder(instance):
    grade_name = unidecode(instance.grade.name).replace(" ", "_")
    subject_name = unidecode(instance.subject.name).replace(" ", "_")

    return f"{grade_name}/{subject_name}"


def material_upload_path(instance):
    return f"tutoring_center/materials/{material_folder(instance)}"


def material_local_path(instance, filename):
    return f"materials/{material_folder(instance)}/{filename}"


class Material(BaseModel, RAGIndexedModel):

    name = models.CharField("Tên tài liệu", max_length=255)
    file_url = CloudinaryField(
        "Tệp trên Cloudinary", folder=material_upload_path, null=True, blank=True
    )
    local_file = models.FileField(
        "Tệp lưu cục bộ",
        upload_to=material_local_path,
        max_length=500,
        null=True,
        blank=True,
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name="Môn học",
    )
    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name="Khối lớp",
    )

    class Meta:
        verbose_name = "Tài liệu"
        verbose_name_plural = "Tài liệu"

    def __str__(self):
        return self.name
