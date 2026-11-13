from django.contrib import admin

from .models import Client, Contract, Interaction, Lead


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'phone', 'stir')
    search_fields = ('name', 'phone', 'stir')
    list_filter = ('kind',)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('number', 'client', 'date', 'end_date', 'amount', 'status')
    list_filter = ('status',)


admin.site.register(Interaction)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'service', 'status', 'created_at')
    list_filter = ('status',)
