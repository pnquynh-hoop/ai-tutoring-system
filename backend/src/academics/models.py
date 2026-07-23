from unidecode import unidecode
from django.db import models
from core.models import BaseModel
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
    name = models.CharField("Khối lớp", max_length=255, unique=True)

    def __str__(self):
        return self.name


def material_upload_path(instance):
    grade_name = unidecode(instance.grade.name).replace(" ", "_")
    subject_name = unidecode(instance.subject.name).replace(" ", "_")

    return f"tutoring_center/materials/{grade_name}/{subject_name}"


class Material(BaseModel):
    name = models.CharField(max_length=255)
    file_url = CloudinaryField(folder=material_upload_path)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="materials"
    )
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="materials")
    is_rag_indexed = models.BooleanField("Đã RAG", default=False)

    def __str__(self):
        return self.name
