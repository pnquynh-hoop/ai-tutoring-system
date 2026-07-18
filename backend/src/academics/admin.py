from django.contrib import admin

from .models import Grade, Material, Subject


class MyAdminSite(admin.AdminSite):
    site_header = "TRANG QUẢN TRỊ HỆ THỐNG VIỆC LÀM BÁN THỜI GIAN"
    index_title = "Quản trị cơ sở dữ liệu"

admin_site = MyAdminSite()

admin_site.register([Subject, Grade, Material])