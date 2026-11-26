import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.permissions import can, section_required
from core.utils import badge_cell, section

from .models import Order

STATUS_LABELS = dict(Order.Status.choices)


def _is_assigned(user, order):
    """Brigadir yoki xodim o'z brigadasining buyurtmasini boshqara oladimi."""
    emp = getattr(user, 'employee_profile', None)
    if emp is None or order.team_id is None:
        return False
    return emp.team_id == order.team_id or order.team.foreman_id == emp.pk


def order_detail(request, obj):
    can_edit = can(request.user, 'orders', 'edit')
    actions = []
    if can_edit:
        flow = {
            'new': [('confirmed', 'Tasdiqlash', 'btn-info'), ('cancelled', 'Bekor qilish', 'btn-outline-danger')],
            'confirmed': [('in_progress', 'Jarayonga olish', 'btn-warning'),
                          ('cancelled', 'Bekor qilish', 'btn-outline-danger')],
            'in_progress': [('done', 'Bajarildi deb belgilash', 'btn-success')],
            'done': [], 'cancelled': [('new', 'Qayta ochish', 'btn-outline-secondary')],
        }
        for status, label, cls in flow.get(obj.status, []):
            actions.append({'label': label, 'url': reverse('orders_status', args=[obj.pk, status]),
                            'method': 'post', 'cls': cls, 'icon': ''})
        if obj.recurrence != Order.Recurrence.NONE and not obj.parent_id:
            actions.append({'label': 'Takroriy buyurtmalarni yaratish', 'url': reverse('orders_recurrences', args=[obj.pk]),
                            'method': 'post', 'cls': 'btn-outline-primary', 'icon': 'bi-arrow-repeat'})
    if can(request.user, 'invoices', 'edit') and obj.status != Order.Status.CANCELLED:
        actions.append({'label': 'Hisob-faktura yaratish', 'url': reverse('invoices_from_order', args=[obj.pk]),
                        'method': 'post', 'cls': 'btn-outline-success', 'icon': 'bi-receipt'})
    elif _is_assigned(request.user, obj) and obj.status in ('confirmed', 'in_progress'):
        nxt = 'in_progress' if obj.status == 'confirmed' else 'done'
        actions.append({'label': 'Boshlash' if nxt == 'in_progress' else 'Bajarildi deb belgilash',
                        'url': reverse('orders_status', args=[obj.pk, nxt]), 'method': 'post',
                        'cls': 'btn-success', 'icon': ''})

    invoices = [({'v': i.number, 'url': reverse('invoices_detail', args=[i.pk])}, i.date, i.amount, i.debt,
                 badge_cell(i.status, i.get_status_display())) for i in obj.invoices.all()]
    children = [({'v': c.number, 'url': reverse('orders_detail', args=[c.pk])}, c.date,
                 badge_cell(c.status, c.get_status_display())) for c in obj.children.all()[:30]]
    review = getattr(obj, 'review', None) if hasattr(obj, 'review') else None
    summary = [
        ('Mijoz', {'v': obj.client.name, 'url': reverse('clients_detail', args=[obj.client_id])}),
        ('Obyekt', {'v': obj.facility.name, 'url': reverse('facilities_detail', args=[obj.facility_id])}),
        ('Xizmat', obj.service.name), ('Sana va vaqt', f'{obj.date:%d.%m.%Y} {obj.time:%H:%M}'),
        ('Holat', badge_cell(obj.status, obj.get_status_display())),
        ('Brigada', obj.team.name if obj.team else None),
        ('Miqdor', obj.quantity), ("Birlik narxi (so'm)", obj.unit_price), ("Jami summa (so'm)", obj.total),
        ('Takrorlanishi', obj.get_recurrence_display()),
        ('Shartnoma', obj.contract.number if obj.contract else None), ('Izoh', obj.note),
    ]
    if review:
        summary.append(('Mijoz bahosi', f'{review.rating}/5 — {review.comment}' if review.comment else f'{review.rating}/5'))
    return {
        'summary': summary,
        'actions': actions,
        'sections': [
            section('Hisob-fakturalar', ['Raqami', 'Sana', 'Summa', 'Qarz', 'Holat'], invoices,
                    empty="Hisob-faktura hali yaratilmagan"),
            section('Takroriy buyurtmalar', ['Raqami', 'Sana', 'Holat'], children, empty="Takroriy buyurtmalar yo'q"),
        ],
    }


@require_POST
def order_status(request, pk, status):
    if not request.user.is_authenticated:
        return redirect('login')
    order = get_object_or_404(Order, pk=pk)
    if status not in STATUS_LABELS:
        raise PermissionDenied
    allowed = can(request.user, 'orders', 'edit') or (
        _is_assigned(request.user, order) and status in ('in_progress', 'done'))
    if not allowed:
        raise PermissionDenied
    old = order.get_status_display()
    order.status = status
    order.save(update_fields=['status'])
    AuditLog.log(request.user, 'update', order, details=f'Holat: {old} → {STATUS_LABELS[status]}')
    messages.success(request, f'Buyurtma holati: {STATUS_LABELS[status]}.')
    nxt = request.POST.get('next')
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                                require_https=request.is_secure()):
        return redirect(nxt)
    return redirect('orders_detail', pk=order.pk)


@section_required('orders', 'edit')
@require_POST
def order_recurrences(request, pk):
    order = get_object_or_404(Order, pk=pk)
    n = order.generate_recurrences()
    AuditLog.log(request.user, 'update', order, details=f'Takroriy buyurtmalar yaratildi: {n}')
    if n:
        messages.success(request, f'{n} ta takroriy buyurtma yaratildi.')
    else:
        messages.info(request, 'Yangi takroriy buyurtma yaratilmadi (barchasi allaqachon mavjud yoki muddat tugagan).')
    return redirect('orders_detail', pk=order.pk)
