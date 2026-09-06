from django import forms
from django.contrib import admin
from core.admin import admin_site
from core.validators import validate_document_upload
from courses.models import (
    Chapter,
    Comment,
    Course,
    Enrollment,
    LearningResource,
    Lesson,
    LessonProgress,
)


class LearningResourceForm(forms.ModelForm):
    class Meta:
        model = LearningResource
        fields = "__all__"

    def clean_file_url(self):
        return validate_document_upload(self.cleaned_data.get("file_url"))


class LearningResourceAdmin(admin.ModelAdmin):
    form = LearningResourceForm


admin_site.register(
    [Course, Chapter, Lesson, LessonProgress, Comment, Enrollment]
)
admin_site.register(LearningResource, LearningResourceAdmin)
