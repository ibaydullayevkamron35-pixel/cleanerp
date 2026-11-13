import calendar
import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import AuditLog
from core.permissions import can, section_required
from core.utils import badge_cell, section

from .models import Attendance, Employee, PayrollRecord

Q2 = Decimal('0.01')


def _can_manage(user):
    return user.is_superuser or user.role in ('admin', 'manager')


# ------------------------------------------------------------------ kartochkalar
def employee_detail(request, obj):
    can_edit = _can_manage(request.user)
    nxt = reverse('employees_detail', args=[obj.pk])
    today = timezone.localdate()
    attendance = [(a.date, a.facility.name if a.facility else None, a.check_in, a.check_out, a.hours,
                   badge_cell(a.status, a.get_status_display()))
                  for a in obj.attendance.select_related('facility')[:10]]
    shifts = [(s.date, s.facility.name, f'{s.start_time:%H:%M} — {s.end_time:%H:%M}', s.note)
              for s in obj.shifts.select_related('facility').filter(date__gte=today).order_by('date')[:10]]
    payroll = [(f'{p.month:02d}.{p.year}', p.base, p.bonus, p.penalty, p.total, "Ha" if p.paid else "Yo'q")
               for p in obj.payroll.all()[:6]]
    return {
        'summary': [
            ('Lavozimi', obj.position), ('Telefon', obj.phone), ('Ishga qabul sanasi', obj.hire_date),
            ('Brigada', obj.team.name if obj.team else None), ('Maosh turi', obj.get_pay_type_display()),
            ("Maosh / stavka (so'm)", obj.pay_rate), ('Holat', badge_cell(obj.status, obj.get_status_display())),
            ('Tizimga kirish hisobi', obj.user.username if obj.user else "Yo'q"),
        ],
        'sections': [
            section('Yaqin smenalar', ['Sana', 'Obyekt', 'Vaqt', 'Izoh'], shifts,
                    add_url=reverse('shifts_add') + f'?employee={obj.pk}&next={nxt}' if can_edit else None,
                    add_label="Smena qo'shish", empty="Smena belgilanmagan"),
            section('Oxirgi davomat', ['Sana', 'Obyekt', 'Keldi', 'Ketdi', 'Soat', 'Holat'], attendance,
                    empty="Davomat kiritilmagan"),
            section('Ish haqi', ['Oy', 'Hisoblangan', 'Bonus', 'Jarima', 'Jami', "To'langan"], payroll,
                    empty="Ish haqi hisoblanmagan"),
        ],
    }


def team_detail(request, obj):
    members = [({'v': m.full_name, 'url': reverse('employees_detail', args=[m.pk])}, m.position, m.phone,
                badge_cell(m.status, m.get_status_display())) for m in obj.members.all()]
    facilities = [({'v': f.name, 'url': reverse('facilities_detail', args=[f.pk])}, f.client.name, f.address)
                  for f in obj.facilities.select_related('client')]
    orders = [({'v': o.number, 'url': reverse('orders_detail', args=[o.pk])}, o.date, o.facility.name,
               badge_cell(o.status, o.get_status_display())) for o in obj.orders.select_related('facility')[:10]]
    return {
        'summary': [('Brigadir', obj.foreman.full_name if obj.foreman else None),
                    ('Xodimlar soni', obj.member_count), ('Izoh', obj.note)],
        'sections': [
            section('Brigada a\'zolari', ['F.I.Sh.', 'Lavozim', 'Telefon', 'Holat'], members, empty="A'zolar yo'q"),
            section('Biriktirilgan obyektlar', ['Obyekt', 'Mijoz', 'Manzil'], facilities, empty="Obyekt biriktirilmagan"),
            section('Oxirgi buyurtmalar', ['Raqami', 'Sana', 'Obyekt', 'Holat'], orders, empty="Buyurtma yo'q"),
        ],
    }


# ------------------------------------------------------------------ ish haqi
def calc_base(emp, year, month):
    first = datetime.date(year, month, 1)
    last = datetime.date(year, month, calendar.monthrange(year, month)[1])
    if emp.pay_type == Employee.PayType.FIXED:
        return Decimal(emp.pay_rate)
    if emp.pay_type == Employee.PayType.HOURLY:
        records = emp.attendance.filter(date__range=(first, last)).exclude(status__in=['absent', 'leave'])
        hours = sum((a.hours for a in records), Decimal('0'))
        return (hours * emp.pay_rate).quantize(Q2, rounding=ROUND_HALF_UP)
    # hajmga qarab: brigadaning bajarilgan m² hajmi a'zolar o'rtasida teng bo'linadi
    if not emp.team_id:
        return Decimal('0')
    from orders.models import Order
    volume = Order.objects.filter(team_id=emp.team_id, status='done', date__range=(first, last),
                                  service__unit='m2').aggregate(s=Sum('quantity'))['s'] or Decimal('0')
    members = emp.team.members.exclude(status=Employee.Status.DISMISSED).count() or 1
    return (Decimal(volume) / members * emp.pay_rate).quantize(Q2, rounding=ROUND_HALF_UP)


@section_required('payroll', 'view')
def payroll(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year') or request.POST.get('year') or today.year)
        month = int(request.GET.get('month') or request.POST.get('month') or today.month)
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            raise ValueError
    except ValueError:
        year, month = today.year, today.month
    editor = can(request.user, 'payroll', 'edit')

    if request.method == 'POST':
        if not editor:
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'generate':
            n = 0
            for emp in Employee.objects.exclude(status=Employee.Status.DISMISSED):
                base = calc_base(emp, year, month)
                rec, created = PayrollRecord.objects.get_or_create(employee=emp, year=year, month=month,
                                                                   defaults={'base': base})
                if not created and not rec.paid:
                    rec.base = base
                    rec.save()
                n += 1
            AuditLog.log(request.user, 'other', details=f'Ish haqi hisoblandi: {month:02d}.{year}', model_name='Ish haqi')
            messages.success(request, f'{month:02d}.{year} uchun {n} ta xodimning ish haqi hisoblandi.')
        elif action == 'pay':
            rec = get_object_or_404(PayrollRecord, pk=request.POST.get('record'))
            if not rec.paid:
                from finance.models import Expense
                rec.paid, rec.paid_date = True, today
                rec.save()
                Expense.objects.create(category='salary', amount=rec.total, date=today,
                                       note=f'Ish haqi: {rec.employee} ({rec.month:02d}.{rec.year})',
                                       created_by=request.user)
                AuditLog.log(request.user, 'update', rec, details="To'landi, xarajat yozildi")
                messages.success(request, f"{rec.employee} ish haqi to'langan deb belgilandi va xarajatlarga yozildi.")
        return redirect(f"{reverse('payroll')}?year={year}&month={month}")

    records = list(PayrollRecord.objects.filter(year=year, month=month).select_related('employee'))
    ctx = {
        'year': year, 'month': month, 'records': records, 'editor': editor,
        'years': range(today.year - 2, today.year + 1),
        'months': [(i, f'{i:02d}') for i in range(1, 13)],
        'total_sum': sum((r.total for r in records), Decimal('0')),
        'paid_sum': sum((r.total for r in records if r.paid), Decimal('0')),
    }
    return render(request, 'hr/payroll.html', ctx)


# ------------------------------------------------------------------ mening vazifalarim
@section_required('my_tasks', 'view')
def my_tasks(request):
    from orders.models import Order

    emp = getattr(request.user, 'employee_profile', None)
    ctx = {'employee': emp}
    if emp:
        today = timezone.localdate()
        cond = Q(pk__in=[])
        if emp.team_id:
            cond |= Q(team_id=emp.team_id)
        cond |= Q(team__foreman=emp)
        orders = (Order.objects.filter(cond).exclude(status__in=['done', 'cancelled'])
                  .filter(date__gte=today - datetime.timedelta(days=1)).select_related('facility', 'service')
                  .order_by('date', 'time')[:30])
        done = (Order.objects.filter(cond, status='done').select_related('facility', 'service')
                .order_by('-date')[:5])
        ctx.update({
            'orders': orders, 'done_orders': done,
            'shifts': emp.shifts.select_related('facility').filter(date__gte=today).order_by('date', 'start_time')[:14],
            'attendance': Attendance.objects.filter(employee=emp, date=today).first(),
            'today': today,
        })
    return render(request, 'hr/my_tasks.html', ctx)


@section_required('my_tasks', 'edit')
@require_POST
def my_checkin(request):
    emp = getattr(request.user, 'employee_profile', None)
    if emp is None:
        messages.error(request, "Sizga xodim kartochkasi biriktirilmagan. Menejerga murojaat qiling.")
        return redirect('my_tasks')
    today = timezone.localdate()
    now = timezone.localtime().time().replace(second=0, microsecond=0)
    action = request.POST.get('action')
    shift = emp.shifts.filter(date=today).select_related('facility').first()
    att, _ = Attendance.objects.get_or_create(employee=emp, date=today,
                                              defaults={'facility': shift.facility if shift else None})
    if action == 'in':
        att.check_in = att.check_in or now
        if att.status in (Attendance.Status.ABSENT, Attendance.Status.LEAVE):
            att.status = Attendance.Status.PRESENT
        att.save()
        messages.success(request, f'Ishga kelganingiz qayd etildi: {att.check_in:%H:%M}.')
    elif action == 'out':
        att.check_out = now
        att.save()
        messages.success(request, f'Ishdan ketganingiz qayd etildi: {now:%H:%M}.')
    return redirect('my_tasks')
