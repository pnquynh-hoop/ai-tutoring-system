from django import forms
from django.contrib import admin

from core.admin import admin_site
from core.validators import validate_image_upload

from .models import StudentProfile, TutorProfile, User


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_avatar(self):
        return validate_image_upload(self.cleaned_data.get("avatar"))


class UserAdmin(admin.ModelAdmin):
    form = UserForm


admin_site.register([StudentProfile, TutorProfile])
admin_site.register(User, UserAdmin)
