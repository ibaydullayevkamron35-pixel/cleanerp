import datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.permissions import can, section_required
from core.utils import badge_cell, money, pdf_font, section

from .models import Invoice, Payment


def invoice_detail(request, obj):
    can_pay = can(request.user, 'payments', 'edit')
    nxt = reverse('invoices_detail', args=[obj.pk])
    payments = [(p.date, p.get_method_display(), p.amount, p.note) for p in obj.payments.all()]
    actions = [{'label': 'PDF yuklab olish', 'url': reverse('invoices_pdf', args=[obj.pk]), 'method': 'get',
                'cls': 'btn-outline-secondary', 'icon': 'bi-file-earmark-pdf'}]
    return {
        'summary': [
            ('Mijoz', {'v': obj.client.name, 'url': reverse('clients_detail', args=[obj.client_id])}),
            ('Buyurtma', {'v': obj.order.number, 'url': reverse('orders_detail', args=[obj.order_id])}
             if obj.order else None),
            ('Sana', obj.date), ("To'lash muddati", obj.due_date),
            ("Summa (so'm)", obj.amount), ("To'langan (so'm)", obj.paid_amount), ("Qarz (so'm)", obj.debt),
            ('Holat', badge_cell(obj.status, obj.get_status_display())),
            ('Muddati o\'tganmi', 'Ha' if obj.is_overdue else "Yo'q"), ('Izoh', obj.note),
        ],
        'actions': actions,
        'sections': [
            section("To'lovlar", ['Sana', 'Usul', 'Summa', 'Izoh'], payments,
                    add_url=reverse('payments_add') + f'?invoice={obj.pk}&next={nxt}'
                    if (can_pay and obj.debt > 0) else None,
                    add_label="To'lov qo'shish", empty="To'lovlar yo'q"),
        ],
    }


@section_required('invoices', 'edit')
@require_POST
def invoice_from_order(request, pk):
    from orders.models import Order

    order = get_object_or_404(Order, pk=pk)
    existing = order.invoices.exclude(status=Invoice.Status.CANCELLED).first()
    if existing:
        messages.info(request, f'Bu buyurtma uchun hisob-faktura allaqachon mavjud: {existing.number}.')
        return redirect('invoices_detail', pk=existing.pk)
    inv = Invoice.objects.create(order=order, client=order.client, amount=order.total, date=timezone.localdate(),
                                 due_date=timezone.localdate() + datetime.timedelta(days=7),
                                 note=f'{order.service.name}, {order.facility.name}', created_by=request.user)
    AuditLog.log(request.user, 'create', inv, details=f'Buyurtma {order.number} asosida')
    messages.success(request, f'Hisob-faktura {inv.number} yaratildi.')
    return redirect('invoices_detail', pk=inv.pk)


def invoice_pdf(request, pk):
    """Hisob-faktura PDF: moliya xodimlari yoki shu mijozning o'zi yuklab oladi."""
    if not request.user.is_authenticated:
        return redirect('login')
    inv = get_object_or_404(Invoice.objects.select_related('client', 'order', 'order__service', 'order__facility'),
                            pk=pk)
    own = inv.client.user_id == request.user.pk
    if not (own or can(request.user, 'invoices', 'view')):
        raise PermissionDenied

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font = pdf_font()
    ss = getSampleStyleSheet()
    title = ParagraphStyle('t', parent=ss['Title'], fontName=font, fontSize=18, alignment=0)
    normal = ParagraphStyle('n', parent=ss['Normal'], fontName=font, fontSize=10, leading=14)
    bold = ParagraphStyle('b', parent=normal, fontSize=11)
    C = settings.COMPANY

    def P(text, style=normal):
        return Paragraph(escape(str(text)), style)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f'Hisob-faktura {inv.number}')
    story = [
        P(f'HISOB-FAKTURA № {inv.number}', title),
        P(f'Sana: {inv.date:%d.%m.%Y}' + (f'    To\'lash muddati: {inv.due_date:%d.%m.%Y}' if inv.due_date else '')),
        Spacer(1, 5 * mm),
        Table([[P('Ijrochi', bold), P('Buyurtmachi', bold)],
               [P(f"{C['name']}\n{C['address']}\nTel: {C['phone']}".replace('\n', ' | ')),
                P(f"{inv.client.name}" + (f" | STIR: {inv.client.stir}" if inv.client.stir else '')
                  + (f" | Tel: {inv.client.phone}" if inv.client.phone else ''))]],
              colWidths=[85 * mm, 85 * mm]),
        Spacer(1, 6 * mm),
    ]
    rows = [[P('Xizmat', bold), P('Miqdor', bold), P('Narx', bold), P('Summa', bold)]]
    order = inv.order
    if order:
        qty = '1' if order.service.unit == 'fixed' else f'{money(order.quantity)} {order.service.unit_short}'
        rows.append([P(f'{order.service.name} — {order.facility.name}'), P(qty), P(money(order.unit_price)),
                     P(money(inv.amount))])
    else:
        rows.append([P(inv.note or 'Xizmat'), P('1'), P(money(inv.amount)), P(money(inv.amount))])
    table = Table(rows, colWidths=[85 * mm, 30 * mm, 28 * mm, 27 * mm])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#94A3B8')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story += [table, Spacer(1, 5 * mm)]
    totals = Table([
        [P('Jami summa:', bold), P(f"{money(inv.amount)} so'm", bold)],
        [P("To'langan:"), P(f"{money(inv.paid_amount)} so'm")],
        [P('Qarz:', bold), P(f"{money(inv.debt)} so'm", bold)],
    ], colWidths=[130 * mm, 40 * mm])
    totals.setStyle(TableStyle([('ALIGN', (1, 0), (1, -1), 'RIGHT')]))
    story += [totals, Spacer(1, 10 * mm), P(f"Holat: {inv.get_status_display()}")]
    doc.build(story)
    from core.utils import archive_to_storage
    archive_to_storage(f'invoices/hisob-faktura-{inv.number}.pdf', buf.getvalue())
    resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="hisob-faktura-{inv.number}.pdf"'
    return resp
