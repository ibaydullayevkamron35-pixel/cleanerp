from django.contrib import admin

from .models import Order, ServiceType


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'price', 'is_active')
    list_filter = ('unit', 'is_active')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'client', 'facility', 'service', 'date', 'status', 'total')
    list_filter = ('status', 'service')
    search_fields = ('number', 'client__name')
    readonly_fields = ('number', 'total')
