from django.contrib import admin
from django.utils import timezone

from .models import NGOProfile


@admin.register(NGOProfile)
class NGOProfileAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "user", "approval_status", "approved_at")
    list_filter = ("approval_status",)
    search_fields = ("organization_name", "user__email")
    actions = ("approve_selected",)

    @admin.action(description="Approve selected NGO profiles")
    def approve_selected(self, request, queryset):
        queryset.exclude(approval_status=NGOProfile.ApprovalStatus.APPROVED).update(
            approval_status=NGOProfile.ApprovalStatus.APPROVED,
            approved_at=timezone.now(),
        )
