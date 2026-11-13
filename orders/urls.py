from django.urls import path

from core.crud import Crud

from . import views
from .models import Order, ServiceType

services = Crud(
    slug='services', url='xizmatlar', model=ServiceType, section='services', title='Xizmatlar va narxlar',
    singular='Xizmat',
    columns=[('Nomi', 'name'), ('Narx birligi', 'unit'), ("Narx (so'm)", 'price'), ('Faol', 'is_active')],
    fields=['name', 'description', 'unit', 'price', 'icon', 'is_active'],
    search=('name', 'description'),
    filters=[('unit', 'unit', 'Narx birligi', ServiceType.Unit.choices)],
    allow_detail=False,
)

orders = Crud(
    slug='orders', url='buyurtmalar', model=Order, section='orders', title='Buyurtmalar', singular='Buyurtma',
    columns=[('Raqami', 'number'), ('Sana', 'date'), ('Vaqt', 'time'), ('Mijoz', 'client'), ('Obyekt', 'facility'),
             ('Xizmat', 'service'), ("Summa (so'm)", 'total'), ('Holat', 'status', 'badge')],
    fields=['client', 'facility', 'service', 'contract', 'team', 'date', 'time', 'quantity', 'unit_price', 'status',
            'recurrence', 'recurrence_end', 'note'],
    search=('number', 'client__name', 'facility__name', 'service__name'),
    filters=[('status', 'status', 'Holat', Order.Status.choices),
             ('service', 'service_id', 'Xizmat', lambda: [(s.pk, s.name) for s in ServiceType.objects.all()])],
    select_related=('client', 'facility', 'service'), ordering=('-date', '-time'),
    export=True, detail_context=views.order_detail,
)

urlpatterns = services.patterns() + orders.patterns() + [
    path('buyurtmalar/<int:pk>/holat/<str:status>/', views.order_status, name='orders_status'),
    path('buyurtmalar/<int:pk>/takrorlash/', views.order_recurrences, name='orders_recurrences'),
]
