from django.contrib import admin

from .models import Complaint, Inspection, InspectionItem, Review


class InspectionItemInline(admin.TabularInline):
    model = InspectionItem
    extra = 0


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ('facility', 'date', 'inspector', 'score')
    inlines = [InspectionItemInline]
    readonly_fields = ('score',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('subject', 'client', 'date', 'status', 'assignee')
    list_filter = ('status',)


admin.site.register(Review)
