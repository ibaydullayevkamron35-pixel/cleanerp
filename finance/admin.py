from django.contrib import admin

from .models import Expense, Invoice, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'client', 'date', 'amount', 'status')
    list_filter = ('status',)
    search_fields = ('number', 'client__name')
    readonly_fields = ('number',)
    inlines = [PaymentInline]


admin.site.register(Payment)
admin.site.register(Expense)
