from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from core.models import BaseModel

"""
    Chứa model User, TutorProfile
"""


class User(AbstractUser):
    email = models.CharField("Địa chỉ thư điện tử", max_length=150, unique=True)
    avatar = CloudinaryField(
        "Ảnh đại diện", null=True, blank=True, folder="tutoring_center/users/"
    )
    phone = models.CharField("Số điện thoại", max_length=10, unique=True)

    def __str__(self):
        return f"{self.email}"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"


class TutorProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.CharField("Giới thiệu ngắn gọn", max_length=255)
    qualification = models.CharField("Trình độ", max_length=255)
    experience_years = models.IntegerField("Số năm kinh nghiệm", default=0)
    is_verified = models.BooleanField("Trạng thái xác minh", default=False)


class StudentProfile(BaseModel):
    class AcademicLevel(models.TextChoices):
        POOR = "POOR", "Yếu"
        AVERAGE = "AVERAGE", "Trung bình"
        GOOD = "GOOD", "Khá"
        EXCELLENT = "EXCELLENT", "Giỏi"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    grade_level = models.ForeignKey(
        "academics.Grade", on_delete=models.SET_NULL, null=True
    )
    learning_goals = models.TextField("Mục tiêu học tập")
    academic_level = models.CharField(
        max_length=20, choices=AcademicLevel.choices, default=AcademicLevel.AVERAGE
    )
