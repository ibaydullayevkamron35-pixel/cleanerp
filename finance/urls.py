from django.urls import path

from core.crud import Crud

from . import views
from .models import Expense, Invoice, Payment

invoices = Crud(
    slug='invoices', url='hisob-fakturalar', model=Invoice, section='invoices', title='Hisob-fakturalar',
    singular='Hisob-faktura',
    columns=[('Raqami', 'number'), ('Sana', 'date'), ('Mijoz', 'client'), ("Summa (so'm)", 'amount'),
             ("Qarz (so'm)", 'debt'), ("To'lash muddati", 'due_date'), ('Holat', 'status', 'badge')],
    fields=['client', 'order', 'date', 'due_date', 'amount', 'status', 'note'],
    search=('number', 'client__name', 'order__number'),
    filters=[('status', 'status', 'Holat', Invoice.Status.choices)],
    select_related=('client', 'order'), export=True, detail_context=views.invoice_detail,
)

payments = Crud(
    slug='payments', url='tolovlar', model=Payment, section='payments', title="To'lovlar", singular="To'lov",
    columns=[('Sana', 'date'), ('Hisob-faktura', 'invoice'), ("Summa (so'm)", 'amount'), ('Usul', 'method'),
             ('Izoh', 'note')],
    fields=['invoice', 'date', 'amount', 'method', 'note'],
    search=('invoice__number', 'invoice__client__name', 'note'),
    filters=[('method', 'method', "To'lov usuli", Payment.Method.choices)],
    select_related=('invoice', 'invoice__client'), allow_detail=False, export=True,
)

expenses = Crud(
    slug='expenses', url='xarajatlar', model=Expense, section='expenses', title='Xarajatlar', singular='Xarajat',
    columns=[('Sana', 'date'), ('Turi', 'category'), ("Summa (so'm)", 'amount'), ('Obyekt', 'facility'),
             ('Izoh', 'note')],
    fields=['category', 'amount', 'date', 'facility', 'note'],
    search=('note', 'facility__name'),
    filters=[('category', 'category', 'Turi', Expense.Category.choices)],
    select_related=('facility',), allow_detail=False, export=True,
)

urlpatterns = invoices.patterns() + payments.patterns() + expenses.patterns() + [
    path('hisob-fakturalar/<int:pk>/pdf/', views.invoice_pdf, name='invoices_pdf'),
    path('buyurtmalar/<int:pk>/hisob-faktura/', views.invoice_from_order, name='invoices_from_order'),
]
