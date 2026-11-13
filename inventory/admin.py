from django.contrib import admin

from .models import InventoryItem, StockMovement, Supplier


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'quantity', 'min_quantity', 'unit', 'is_active')
    list_filter = ('kind', 'is_active')
    readonly_fields = ('quantity',)


admin.site.register(StockMovement)
admin.site.register(Supplier)
