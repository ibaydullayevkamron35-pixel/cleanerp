from django.urls import reverse

from core.utils import badge_cell, section


def facility_detail(request, obj):
    can_edit = request.user.is_superuser or request.user.role in ('admin', 'manager')
    nxt = reverse('facilities_detail', args=[obj.pk])
    q = f'?facility={obj.pk}&next={nxt}'

    zones = [(
        {'v': z.name, 'url': reverse('zones_edit', args=[z.pk]) + f'?next={nxt}' if can_edit else None},
        z.area, z.get_cleaning_type_display()) for z in obj.zones.all()]
    schedules = [(
        {'v': s.get_frequency_display(), 'url': reverse('schedules_edit', args=[s.pk]) + f'?next={nxt}'
         if can_edit else None},
        s.service.name, s.when, 'Faol' if s.is_active else 'Nofaol') for s in obj.schedules.select_related('service')]
    orders = [(
        {'v': o.number, 'url': reverse('orders_detail', args=[o.pk])}, o.date, o.service.name, o.total,
        badge_cell(o.status, o.get_status_display())) for o in obj.orders.select_related('service')[:10]]
    inspections = [(
        {'v': i.date, 'url': reverse('inspections_detail', args=[i.pk])}, i.score,
        i.inspector.full_name if i.inspector else None) for i in obj.inspections.select_related('inspector')[:10]]
    teams = [(t.name, t.foreman.full_name if t.foreman else None, t.member_count) for t in obj.teams.all()]
    staff = [(e.full_name, e.position, e.phone) for e in obj.employees.all()]

    return {
        'summary': [
            ('Mijoz', {'v': obj.client.name, 'url': reverse('clients_detail', args=[obj.client_id])}),
            ('Turi', obj.get_kind_display()), ('Manzil', obj.address), ('Umumiy maydon (m²)', obj.area),
            ('Qavatlar soni', obj.floors), ('Holat', badge_cell(obj.status, obj.get_status_display())),
            ('Tozalash talablari', obj.requirements), ("Maxsus ko'rsatmalar", obj.instructions),
        ],
        'sections': [
            section('Xonalar va zonalar', ['Nomi', 'Maydon (m²)', 'Tozalash turi'], zones,
                    add_url=reverse('zones_add') + q if can_edit else None, add_label="Zona qo'shish",
                    empty="Zonalar kiritilmagan"),
            section('Tozalash jadvali', ['Davriylik', 'Xizmat', 'Qachon', 'Holat'], schedules,
                    add_url=reverse('schedules_add') + q if can_edit else None, add_label="Jadval qo'shish",
                    empty="Jadval tuzilmagan"),
            section('Biriktirilgan brigadalar', ['Brigada', 'Brigadir', 'Xodimlar soni'], teams,
                    empty="Brigada biriktirilmagan (tahrirlash orqali biriktiring)"),
            section('Biriktirilgan xodimlar', ['F.I.Sh.', 'Lavozim', 'Telefon'], staff,
                    empty="Xodim biriktirilmagan"),
            section('Oxirgi buyurtmalar', ['Raqami', 'Sana', 'Xizmat', "Summa (so'm)", 'Holat'], orders,
                    add_url=reverse('orders_add') + f'?client={obj.client_id}&facility={obj.pk}&next={nxt}'
                    if can_edit else None, add_label="Buyurtma qo'shish", empty="Buyurtmalar yo'q"),
            section('Tekshiruvlar tarixi', ['Sana', 'Ball (%)', 'Tekshiruvchi'], inspections,
                    empty="Tekshiruvlar o'tkazilmagan"),
        ],
    }
