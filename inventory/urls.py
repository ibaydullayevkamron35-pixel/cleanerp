from django.urls import path

from core.crud import Crud

from . import views
from .forms import MovementForm
from .models import InventoryItem, StockMovement, Supplier

items = Crud(
    slug='inventory', url='ombor', model=InventoryItem, section='inventory', title='Ombor: mahsulotlar',
    singular='Mahsulot',
    columns=[('Nomi', 'name'), ('Turi', 'kind'), ('Qoldiq', 'quantity'), ('Birligi', 'unit'),
             ('Minimal qoldiq', 'min_quantity'), ('Holat', 'stock_label')],
    fields=['name', 'kind', 'unit', 'min_quantity', 'price', 'is_active'],
    search=('name',),
    filters=[('kind', 'kind', 'Turi', InventoryItem.Kind.choices)],
    export=True, detail_context=views.item_detail,
    hint="Boshlang'ich qoldiq «Kirim-chiqim» bo'limida «Kirim» sifatida kiritiladi.",
)

movements = Crud(
    slug='movements', url='harakatlar', model=StockMovement, section='movements', title='Kirim-chiqim',
    singular='Harakat',
    columns=[('Sana', 'date'), ('Turi', 'kind', 'badge'), ('Mahsulot', 'item'), ('Miqdor', 'quantity'),
             ('Obyekt', 'facility'), ('Xodim', 'employee'), ('Yetkazib beruvchi', 'supplier')],
    form_class=MovementForm,
    search=('item__name', 'facility__name', 'employee__full_name', 'supplier__name'),
    filters=[('kind', 'kind', 'Turi', StockMovement.Kind.choices),
             ('item', 'item_id', 'Mahsulot', lambda: [(i.pk, i.name) for i in InventoryItem.objects.all()])],
    select_related=('item', 'facility', 'employee', 'supplier'), ordering=('-date', '-id'),
    allow_edit=False, allow_detail=False, export=True,
)

suppliers = Crud(
    slug='suppliers', url='yetkazib-beruvchilar', model=Supplier, section='suppliers',
    title='Yetkazib beruvchilar', singular='Yetkazib beruvchi',
    columns=[('Nomi', 'name'), ('Telefon', 'phone'), ('Manzil', 'address'), ('Izoh', 'note')],
    fields=['name', 'phone', 'address', 'note'], search=('name', 'phone'), allow_detail=False,
)

urlpatterns = items.patterns() + movements.patterns() + suppliers.patterns() + [
    path('ombor/inventarizatsiya/', views.inventory_count, name='inventory_count'),
]
