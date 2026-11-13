from django.contrib import admin

from .models import CleaningSchedule, Facility, Zone


class ZoneInline(admin.TabularInline):
    model = Zone
    extra = 0


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'kind', 'area', 'status')
    list_filter = ('kind', 'status')
    search_fields = ('name', 'address', 'client__name')
    inlines = [ZoneInline]


admin.site.register(CleaningSchedule)
