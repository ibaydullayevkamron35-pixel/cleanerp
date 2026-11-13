from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (('CleanERP', {'fields': ('role', 'phone', 'photo')}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (('CleanERP', {'fields': ('role', 'phone')}),)
    list_display = ('username', 'get_full_name', 'role', 'phone', 'is_active')
    list_filter = ('role', 'is_active')
