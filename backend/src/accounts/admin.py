from django.contrib import admin
from .models import StudentProfile, TutorProfile, User

admin.site.register([User, StudentProfile, TutorProfile])