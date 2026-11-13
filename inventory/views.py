from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from core.permissions import can, section_required
from core.utils import badge_cell, section

from .models import InventoryItem, StockMovement


def item_detail(request, obj):
    movements = [(m.date, badge_cell(m.kind, m.get_kind_display()), m.quantity,
                  m.facility.name if m.facility else None, m.employee.full_name if m.employee else None,
                  m.supplier.name if m.supplier else None, m.note)
                 for m in obj.movements.select_related('facility', 'employee', 'supplier')[:20]]
    can_edit = can(request.user, 'movements', 'edit')
    return {
        'summary': [
            ('Turi', obj.get_kind_display()), ('Birligi', obj.unit), ('Qoldiq', f'{obj.quantity} {obj.unit}'),
            ('Minimal qoldiq', f'{obj.min_quantity} {obj.unit}'),
            ('Holat', {'v': obj.stock_label(), 'badge': 'danger' if obj.is_low else 'success'}),
            ("Narxi (so'm)", obj.price), ('Faol', obj.is_active),
        ],
        'sections': [
            section('Oxirgi harakatlar', ['Sana', 'Turi', 'Miqdor', 'Obyekt', 'Xodim', 'Yetkazib beruvchi', 'Izoh'],
                    movements,
                    add_url=reverse('movements_add') + f'?item={obj.pk}&next={reverse("inventory_detail", args=[obj.pk])}'
                    if can_edit else None, add_label='Kirim/chiqim qo\'shish', empty="Harakatlar yo'q"),
        ],
    }


@section_required('movements', 'edit')
def inventory_count(request):
    """Inventarizatsiya: haqiqiy qoldiq kiritiladi, farq 'Tuzatish' harakati sifatida yoziladi."""
    items = InventoryItem.objects.filter(is_active=True).order_by('name')
    if request.method == 'POST':
        changed = 0
        with transaction.atomic():
            for item in items:
                raw = (request.POST.get(f'actual_{item.pk}') or '').strip().replace(',', '.')
                if raw == '':
                    continue
                try:
                    actual = Decimal(raw)
                except InvalidOperation:
                    messages.error(request, f'«{item.name}» uchun noto\'g\'ri son: {raw}')
                    continue
                diff = actual - item.quantity
                if diff != 0:
                    StockMovement.objects.create(
                        item=item, kind=StockMovement.Kind.ADJUST, quantity=diff, date=timezone.localdate(),
                        note=f'Inventarizatsiya: {item.quantity} → {actual}', created_by=request.user)
                    changed += 1
        AuditLog.log(request.user, 'other', details=f'Inventarizatsiya: {changed} ta tuzatish', model_name='Ombor')
        messages.success(request, f'Inventarizatsiya saqlandi. Tuzatilgan mahsulotlar: {changed}.')
        return redirect('inventory_list')
    return render(request, 'inventory/count.html', {'items': items})
