from django.contrib import admin
from .models import Grade, Material, Subject

admin.site.register([Grade, Material, Subject])
