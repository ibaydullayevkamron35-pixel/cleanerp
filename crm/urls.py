from django.urls import path

from core.crud import Crud

from . import views
from .models import Client, Contract, Interaction, Lead

clients = Crud(
    slug='clients', url='mijozlar', model=Client, section='clients', title='Mijozlar', singular='Mijoz',
    columns=[('Nomi', 'name'), ('Turi', 'kind'), ('Telefon', 'phone'), ('STIR', 'stir'), ('Manzil', 'address'),
             ("Qarzdorlik (so'm)", 'total_debt')],
    fields=['kind', 'name', 'stir', 'contact_person', 'phone', 'email', 'address', 'note'],
    search=('name', 'phone', 'stir', 'email', 'address'),
    filters=[('kind', 'kind', 'Turi', Client.Kind.choices)],
    export=True, detail_context=views.client_detail,
)

contracts = Crud(
    slug='contracts', url='shartnomalar', model=Contract, section='contracts', title='Shartnomalar',
    singular='Shartnoma',
    columns=[('Raqami', 'number'), ('Mijoz', 'client'), ('Sana', 'date'), ('Muddati', 'end_date'),
             ("Summa (so'm)", 'amount'), ('Holat', 'status', 'badge')],
    fields=['client', 'number', 'date', 'end_date', 'amount', 'status', 'note'],
    search=('number', 'client__name'),
    filters=[('status', 'status', 'Holat', Contract.Status.choices)],
    select_related=('client',),
)

interactions = Crud(
    slug='interactions', url='murojaatlar', model=Interaction, section='clients',
    title='Murojaatlar va muloqotlar', singular='Murojaat',
    columns=[('Sana', 'date'), ('Mijoz', 'client'), ('Kanal', 'channel'), ('Mavzu', 'subject')],
    fields=['client', 'date', 'channel', 'subject', 'text'],
    search=('subject', 'client__name', 'text'),
    filters=[('channel', 'channel', 'Kanal', Interaction.Channel.choices)],
    select_related=('client',), allow_detail=False,
)

leads = Crud(
    slug='leads', url='arizalar', model=Lead, section='leads', title='Saytdan kelgan arizalar', singular='Ariza',
    columns=[('Kelgan vaqt', 'created_at'), ('Ismi', 'name'), ('Telefon', 'phone'), ('Xizmat', 'service'),
             ('Holat', 'status', 'badge')],
    fields=['name', 'phone', 'service', 'address', 'message', 'status'],
    search=('name', 'phone', 'message'),
    filters=[('status', 'status', 'Holat', Lead.Status.choices)],
    select_related=('service',), detail_context=views.lead_detail,
)

urlpatterns = (
    clients.patterns() + contracts.patterns() + interactions.patterns() + leads.patterns()
    + [path('arizalar/<int:pk>/aylantirish/', views.lead_convert, name='leads_convert')]
)
