from django.contrib import admin

from .models import Attendance, Employee, PayrollRecord, Shift, Team


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'team', 'pay_type', 'status')
    list_filter = ('status', 'pay_type', 'team')
    search_fields = ('full_name', 'phone')


admin.site.register(Team)
admin.site.register(Shift)
admin.site.register(Attendance)
admin.site.register(PayrollRecord)
