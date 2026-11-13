from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.permissions import section_required
from core.utils import badge_cell, section

from .models import Client, Lead


def client_detail(request, obj):
    can_edit = request.user.is_superuser or request.user.role in ('admin', 'manager')
    nxt = reverse('clients_detail', args=[obj.pk])

    facilities = [
        (
            {'v': f.name, 'url': reverse('facilities_detail', args=[f.pk])},
            f.get_kind_display(), f.address, f.area, badge_cell(f.status, f.get_status_display()),
        ) for f in obj.facilities.all()
    ]
    contracts = [
        (
            {'v': c.number, 'url': reverse('contracts_detail', args=[c.pk])},
            c.date, c.end_date, c.amount, badge_cell(c.status, c.get_status_display()),
        ) for c in obj.contracts.all()
    ]
    orders = [
        (
            {'v': o.number, 'url': reverse('orders_detail', args=[o.pk])},
            o.date, o.service.name, o.facility.name, o.total, badge_cell(o.status, o.get_status_display()),
        ) for o in obj.orders.select_related('service', 'facility')[:15]
    ]
    invoices = [
        (
            {'v': i.number, 'url': reverse('invoices_detail', args=[i.pk])},
            i.date, i.amount, i.paid_amount, i.debt, badge_cell(i.status, i.get_status_display()),
        ) for i in obj.invoices.all()[:15]
    ]
    talks = [(t.date, t.get_channel_display(), t.subject, t.text) for t in obj.interactions.all()[:15]]

    q = f'?client={obj.pk}&next={nxt}'
    return {
        'summary': [
            ('Turi', obj.get_kind_display()), ('STIR', obj.stir), ('Aloqa uchun shaxs', obj.contact_person),
            ('Telefon', obj.phone), ('Email', obj.email), ('Manzil', obj.address),
            ("Umumiy qarzdorlik (so'm)", obj.total_debt()), ('Izoh', obj.note),
            ('Kabinet hisobi', obj.user.username if obj.user else 'Yo\'q'),
        ],
        'sections': [
            section('Obyektlar', ['Nomi', 'Turi', 'Manzil', 'Maydon (m²)', 'Holat'], facilities,
                    add_url=reverse('facilities_add') + q if can_edit else None, add_label="Obyekt qo'shish",
                    empty="Mijozda hali obyekt yo'q"),
            section('Shartnomalar', ['Raqami', 'Sana', 'Muddati', "Summa (so'm)", 'Holat'], contracts,
                    add_url=reverse('contracts_add') + q if can_edit else None, add_label="Shartnoma qo'shish",
                    empty="Shartnoma yo'q"),
            section('Oxirgi buyurtmalar', ['Raqami', 'Sana', 'Xizmat', 'Obyekt', "Summa (so'm)", 'Holat'], orders,
                    add_url=reverse('orders_add') + q if can_edit else None, add_label="Buyurtma qo'shish",
                    empty="Buyurtma yo'q"),
            section('Hisob-fakturalar', ['Raqami', 'Sana', 'Summa', "To'langan", 'Qarz', 'Holat'], invoices,
                    empty="Hisob-faktura yo'q"),
            section('Murojaatlar va muloqotlar', ['Sana', 'Kanal', 'Mavzu', 'Mazmuni'], talks,
                    add_url=reverse('interactions_add') + q if can_edit else None, add_label="Murojaat qo'shish",
                    empty="Muloqotlar tarixi bo'sh"),
        ],
    }


def lead_detail(request, obj):
    actions = []
    can_edit = request.user.is_superuser or request.user.role in ('admin', 'manager')
    if can_edit and obj.status != Lead.Status.CONVERTED:
        actions.append({'label': 'Mijozga aylantirish', 'url': reverse('leads_convert', args=[obj.pk]),
                        'method': 'post', 'cls': 'btn-success', 'icon': 'bi-person-plus'})
    return {
        'summary': [
            ('Ismi', obj.name), ('Telefon', obj.phone), ('Xizmat', obj.service.name if obj.service else None),
            ('Manzil', obj.address), ('Xabar', obj.message),
            ('Holat', badge_cell(obj.status, obj.get_status_display())), ('Kelgan vaqt', obj.created_at),
        ],
        'actions': actions,
    }


@section_required('leads', 'edit')
@require_POST
def lead_convert(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    client = Client.objects.create(kind=Client.Kind.INDIVIDUAL, name=lead.name, phone=lead.phone,
                                   address=lead.address, note=f'Saytdagi arizadan: {lead.message}'[:500])
    lead.status = Lead.Status.CONVERTED
    lead.save(update_fields=['status'])
    AuditLog.log(request.user, 'create', client, details=f'Arizadan #{lead.pk}')
    messages.success(request, f'«{client.name}» mijozlar ro\'yxatiga qo\'shildi.')
    return redirect('clients_detail', pk=client.pk)
