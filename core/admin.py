from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'model_name', 'object_repr')
    list_filter = ('action',)
    search_fields = ('object_repr', 'model_name', 'user__username')
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False
