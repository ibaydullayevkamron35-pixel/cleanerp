import datetime
from decimal import Decimal

from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from core.permissions import can, section_required
from core.utils import PERIODS, add_months, get_period, pdf_table_response, to_cell, xlsx_response

ZERO = Decimal('0')
MONTH_NAMES = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']


def _sum(qs, field='amount'):
    return qs.aggregate(s=Sum(field))['s'] or ZERO


# ================================================================== DASHBOARD
@section_required('dashboard')
def dashboard(request):
    from crm.models import Lead
    from facilities.models import Facility
    from finance.models import Expense, Invoice, Payment
    from hr.models import Employee, Team
    from inventory.models import InventoryItem
    from orders.models import Order
    from quality.models import Complaint

    today = timezone.localdate()
    start, end, period = get_period(request)
    month_start = today.replace(day=1)

    period_orders = Order.objects.filter(date__range=(start, end)).exclude(status='cancelled')
    invoiced = Invoice.objects.exclude(status='cancelled')
    total_debt = max(_sum(invoiced) - _sum(Payment.objects.exclude(invoice__status='cancelled')), ZERO)

    kpis = {
        'orders_today': Order.objects.filter(date=today).exclude(status='cancelled').count(),
        'orders_period': period_orders.count(),
        'facilities': Facility.objects.filter(status='active').count(),
        'employees': Employee.objects.filter(status='active').count(),
        'revenue_period': _sum(Payment.objects.filter(date__range=(start, end))),
        'expense_period': _sum(Expense.objects.filter(date__range=(start, end))),
        'revenue_month': _sum(Payment.objects.filter(date__gte=month_start, date__lte=today)),
        'debt': total_debt,
        'overdue': invoiced.filter(status__in=['unpaid', 'partial'], due_date__lt=today).count(),
        'new_leads': Lead.objects.filter(status='new').count(),
        'open_complaints': Complaint.objects.filter(status__in=['new', 'in_progress']).count(),
    }
    kpis['profit_period'] = kpis['revenue_period'] - kpis['expense_period']

    low_stock = InventoryItem.objects.filter(is_active=True, quantity__lte=F('min_quantity')).order_by('quantity')[:6]
    recent_orders = Order.objects.select_related('client', 'facility', 'service').order_by('-created_at')[:8]
    today_orders = (Order.objects.filter(date=today).exclude(status='cancelled')
                    .select_related('client', 'facility', 'service', 'team').order_by('time')[:8])

    # --- grafiklar
    first = add_months(month_start, -5)
    months = [add_months(first, i) for i in range(6)]
    rev = {(r['m'].year, r['m'].month): r['s'] for r in
           Payment.objects.filter(date__gte=first).annotate(m=TruncMonth('date')).values('m').annotate(s=Sum('amount'))}
    exp = {(r['m'].year, r['m'].month): r['s'] for r in
           Expense.objects.filter(date__gte=first).annotate(m=TruncMonth('date')).values('m').annotate(s=Sum('amount'))}
    services = list(period_orders.values('service__name').annotate(n=Count('id')).order_by('-n')[:8])
    teams = list(Team.objects.annotate(
        done=Count('orders', filter=Q(orders__status='done', orders__date__range=(start, end))),
        rating=Avg('orders__review__rating')).order_by('-done')[:8])
    chart = {
        'months': [f'{MONTH_NAMES[m.month - 1]} {m.year % 100:02d}' for m in months],
        'revenue': [float(rev.get((m.year, m.month), 0)) for m in months],
        'expenses': [float(exp.get((m.year, m.month), 0)) for m in months],
        'services': {'labels': [s['service__name'] for s in services], 'values': [s['n'] for s in services]},
        'teams': {'labels': [t.name for t in teams], 'done': [t.done for t in teams],
                  'rating': [round(float(t.rating), 2) if t.rating else 0 for t in teams]},
    }
    return render(request, 'reports/dashboard.html', {
        'kpis': kpis, 'low_stock': low_stock, 'recent_orders': recent_orders, 'today_orders': today_orders,
        'chart': chart, 'periods': PERIODS, 'period': period, 'start': start, 'end': end,
    })


# ================================================================== HISOBOTLAR
def r_orders(start, end):
    from orders.models import Order

    qs = Order.objects.filter(date__range=(start, end)).select_related('client', 'facility', 'service').order_by('date')
    rows = [(o.number, o.date, o.client.name, o.facility.name, o.service.name, o.get_status_display(), o.total)
            for o in qs]
    active = qs.exclude(status='cancelled')
    summary = [('Buyurtmalar soni', qs.count()), ('Bajarilgan', qs.filter(status='done').count()),
               ('Bekor qilingan', qs.filter(status='cancelled').count()),
               ("Jami summa (so'm), bekor qilinmaganlar", _sum(active, 'total'))]
    return ['Raqami', 'Sana', 'Mijoz', 'Obyekt', 'Xizmat', 'Holat', "Summa (so'm)"], rows, summary


def r_finance(start, end):
    from finance.models import Expense, Payment

    pays = Payment.objects.filter(date__range=(start, end)).select_related('invoice', 'invoice__client')
    exps = Expense.objects.filter(date__range=(start, end))
    entries = [(p.date, 'Daromad', f'{p.invoice.number} — {p.invoice.client.name} ({p.get_method_display()})',
                p.amount, None) for p in pays]
    entries += [(e.date, 'Xarajat', f'{e.get_category_display()}: {e.note}'.strip(': '), None, e.amount)
                for e in exps]
    entries.sort(key=lambda r: r[0])
    income, expense = _sum(pays), _sum(exps)
    return (['Sana', 'Turi', 'Izoh', "Kirim (so'm)", "Chiqim (so'm)"], entries,
            [("Daromad (so'm)", income), ("Xarajat (so'm)", expense), ("Foyda (so'm)", income - expense)])


def r_profit(start, end):
    from facilities.models import Facility
    from finance.models import Expense, Payment

    rows, ti, te = [], ZERO, ZERO
    for f in Facility.objects.select_related('client'):
        income = _sum(Payment.objects.filter(date__range=(start, end), invoice__order__facility=f))
        expense = _sum(Expense.objects.filter(date__range=(start, end), facility=f))
        if income or expense:
            rows.append((f.name, f.client.name, income, expense, income - expense))
            ti, te = ti + income, te + expense
    rows.sort(key=lambda r: r[4], reverse=True)
    return (['Obyekt', 'Mijoz', "Daromad (so'm)", "Xarajat (so'm)", "Foyda (so'm)"], rows,
            [("Daromad (so'm)", ti), ("Xarajat (so'm)", te), ("Foyda (so'm)", ti - te)])


def r_debts(start, end):
    from finance.models import Invoice

    today = timezone.localdate()
    rows, total = [], ZERO
    for i in Invoice.objects.exclude(status__in=['paid', 'cancelled']).select_related('client').order_by('due_date'):
        debt = i.debt
        if debt > 0:
            overdue = 'Ha' if (i.due_date and i.due_date < today) else "Yo'q"
            rows.append((i.number, i.client.name, i.date, i.due_date, i.amount, i.paid_amount, debt, overdue))
            total += debt
    return (['Raqami', 'Mijoz', 'Sana', 'Muddati', 'Summa', "To'langan", 'Qarz', "Muddati o'tgan"], rows,
            [("Jami qarzdorlik (so'm)", total), ('Qarzdor hisob-fakturalar', len(rows)),
             ("Eslatma", "Qarzdorlik tanlangan davrga qaramay, barcha ochiq hisob-fakturalar bo'yicha")])


def r_inventory(start, end):
    from inventory.models import InventoryItem, StockMovement

    qs = (StockMovement.objects.filter(date__range=(start, end))
          .select_related('item', 'facility', 'employee', 'supplier').order_by('date', 'id'))
    rows = [(m.date, m.item.name, m.get_kind_display(), m.quantity, m.item.unit,
             m.facility.name if m.facility else None, m.employee.full_name if m.employee else None,
             m.supplier.name if m.supplier else None) for m in qs]
    low = InventoryItem.objects.filter(is_active=True, quantity__lte=F('min_quantity')).count()
    return (['Sana', 'Mahsulot', 'Turi', 'Miqdor', 'Birlik', 'Obyekt', 'Xodim', 'Yetkazib beruvchi'], rows,
            [('Harakatlar soni', len(rows)), ('Qoldig\'i kam mahsulotlar', low)])


def r_attendance(start, end):
    from hr.models import Attendance, Employee

    stats = {}
    for a in Attendance.objects.filter(date__range=(start, end)).select_related('employee'):
        s = stats.setdefault(a.employee_id, {'emp': a.employee, 'present': 0, 'late': 0, 'absent': 0, 'leave': 0,
                                             'hours': ZERO})
        s[a.status] += 1
        s['hours'] += a.hours
    rows = [(s['emp'].full_name, s['present'], s['late'], s['absent'], s['leave'], s['hours'])
            for s in sorted(stats.values(), key=lambda x: x['emp'].full_name)]
    return (['Xodim', 'Keldi', 'Kechikdi', 'Kelmadi', "Ruxsat / ta'til", 'Ishlagan soat'], rows,
            [('Xodimlar soni', len(rows)), ('Kechikishlar', sum(r[2] for r in rows)),
             ('Kelmaganlar (kun)', sum(r[3] for r in rows))])


def r_quality(start, end):
    from quality.models import Complaint, Inspection, Review

    ins = Inspection.objects.filter(date__range=(start, end)).select_related('facility', 'inspector').order_by('date')
    rows = [(i.date, i.facility.name, i.inspector.full_name if i.inspector else None, i.score) for i in ins]
    avg_ins = ins.aggregate(a=Avg('score'))['a']
    reviews = Review.objects.filter(date__range=(start, end))
    avg_rev = reviews.aggregate(a=Avg('rating'))['a']
    complaints = Complaint.objects.filter(date__range=(start, end))
    return (['Sana', 'Obyekt', 'Tekshiruvchi', 'Ball (%)'], rows,
            [("O'rtacha tekshiruv balli (%)", round(avg_ins, 1) if avg_ins is not None else None),
             ("Mijozlarning o'rtacha bahosi (1-5)", round(avg_rev, 2) if avg_rev is not None else None),
             ('Baholar soni', reviews.count()), ('Shikoyatlar', complaints.count()),
             ('Hal qilinmagan shikoyatlar', complaints.filter(status__in=['new', 'in_progress']).count())])


REPORTS = {
    'orders': ('Buyurtmalar hisoboti', r_orders),
    'finance': ('Moliyaviy hisobot (daromad va xarajat)', r_finance),
    'profit': ('Foyda: obyektlar kesimida', r_profit),
    'debts': ('Qarzdorlik hisoboti', r_debts),
    'inventory': ('Ombor harakati hisoboti', r_inventory),
    'attendance': ('Davomat hisoboti', r_attendance),
    'quality': ('Sifat nazorati hisoboti', r_quality),
}


@section_required('reports')
def reports(request):
    code = request.GET.get('type', 'orders')
    if code not in REPORTS:
        code = 'orders'
    start, end, period = get_period(request)
    title, fn = REPORTS[code]
    headers, rows, summary = fn(start, end)

    export = request.GET.get('export')
    fname = f'{code}_{start:%Y%m%d}_{end:%Y%m%d}'
    if export == 'xlsx':
        return xlsx_response(fname, title, headers, rows)
    if export == 'pdf':
        footer = [[f'{k}: {to_cell(v)["v"]}'] + [''] * (len(headers) - 1) for k, v in summary]
        return pdf_table_response(fname, title, headers, rows, subtitle=f'{start:%d.%m.%Y} — {end:%d.%m.%Y}',
                                  footer_rows=footer)
    params = request.GET.copy()
    params.pop('export', None)
    return render(request, 'reports/index.html', {
        'code': code, 'title': title, 'headers': headers,
        'rows': [[to_cell(c) for c in r] for r in rows],
        'summary': [(k, to_cell(v)) for k, v in summary],
        'types': [(k, v[0]) for k, v in REPORTS.items()],
        'periods': PERIODS, 'period': period, 'start': start, 'end': end,
        'query': params.urlencode(),
    })
