from django.contrib import admin
from django.urls import reverse


class TutoringAdminSite(admin.AdminSite):
    site_header = "Trung tâm gia sư Novi"
    site_title = "Quản trị hệ thống"
    index_title = "Bảng điều khiển"
    index_template = "admin/tutoring_index.html"

    def __init__(self, name="admin"):
        super().__init__(name)
        self.nav_entries = []

    def register_nav_link(self, url_name, label, description):
        self.nav_entries.append(
            {"url_name": url_name, "label": label, "description": description}
        )

    def nav_links(self):
        return [
            {
                "label": entry["label"],
                "description": entry["description"],
                "url": reverse(f"admin:{entry['url_name']}"),
            }
            for entry in self.nav_entries
        ]

    def each_context(self, request):
        context = super().each_context(request)
        context["nav_links"] = self.nav_links()
        return context


admin_site = TutoringAdminSite(name="admin")
