from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteReport


@admin.register(SiteReport)
class SiteReportAdmin(ModelAdmin):
    list_display = ["domain", "overall_grade", "overall_score", "paid", "created_at"]
    list_filter = ["overall_grade", "paid", "created_at"]
    search_fields = ["domain", "url"]
    readonly_fields = ["id", "created_at"]
