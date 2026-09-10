from django.contrib import admin


class TutoringAdminSite(admin.AdminSite):
    site_header = "Trung tâm gia sư Novi"
    site_title = "Quản trị hệ thống"
    index_title = "Bảng điều khiển"


admin_site = TutoringAdminSite(name="admin")
