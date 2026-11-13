from django.urls import path

from core.crud import Crud

from . import views
from .forms import EmployeeForm
from .models import Attendance, Employee, PayrollRecord, Shift, Team

employees = Crud(
    slug='employees', url='xodimlar', model=Employee, section='employees', title='Xodimlar', singular='Xodim',
    columns=[('F.I.Sh.', 'full_name'), ('Lavozimi', 'position'), ('Telefon', 'phone'), ('Brigada', 'team'),
             ('Maosh turi', 'pay_type'), ('Holat', 'status', 'badge')],
    form_class=EmployeeForm,
    search=('full_name', 'phone', 'position'),
    filters=[('status', 'status', 'Holat', Employee.Status.choices),
             ('team', 'team_id', 'Brigada', lambda: [(t.pk, t.name) for t in Team.objects.all()])],
    select_related=('team',), export=True, detail_context=views.employee_detail,
)

teams = Crud(
    slug='teams', url='brigadalar', model=Team, section='teams', title='Brigadalar', singular='Brigada',
    columns=[('Nomi', 'name'), ('Brigadir', 'foreman'), ('Xodimlar soni', 'member_count'), ('Izoh', 'note')],
    fields=['name', 'foreman', 'note'], search=('name',), select_related=('foreman',),
    detail_context=views.team_detail,
)

shifts = Crud(
    slug='shifts', url='jadval', model=Shift, section='shifts', title='Ish jadvali (smenalar)', singular='Smena',
    columns=[('Sana', 'date'), ('Xodim', 'employee'), ('Obyekt', 'facility'), ('Boshlanishi', 'start_time'),
             ('Tugashi', 'end_time'), ('Buyurtma', 'order')],
    fields=['employee', 'facility', 'order', 'date', 'start_time', 'end_time', 'note'],
    search=('employee__full_name', 'facility__name'),
    filters=[('employee', 'employee_id', 'Xodim', lambda: [(e.pk, e.full_name) for e in Employee.objects.all()])],
    select_related=('employee', 'facility', 'order'), ordering=('-date', 'start_time'), allow_detail=False,
)

attendance = Crud(
    slug='attendance', url='davomat', model=Attendance, section='attendance', title='Davomat jurnali',
    singular='Davomat yozuvi',
    columns=[('Sana', 'date'), ('Xodim', 'employee'), ('Obyekt', 'facility'), ('Keldi', 'check_in'),
             ('Ketdi', 'check_out'), ('Soat', 'hours'), ('Holat', 'status', 'badge')],
    fields=['employee', 'date', 'facility', 'check_in', 'check_out', 'status', 'note'],
    search=('employee__full_name', 'facility__name'),
    filters=[('status', 'status', 'Holat', Attendance.Status.choices),
             ('employee', 'employee_id', 'Xodim', lambda: [(e.pk, e.full_name) for e in Employee.objects.all()])],
    select_related=('employee', 'facility'), ordering=('-date', 'employee__full_name'), allow_detail=False,
    export=True,
)

payroll_records = Crud(
    slug='payroll_records', url='ish-haqi/yozuvlar', model=PayrollRecord, section='payroll',
    title='Ish haqi yozuvlari', singular='Ish haqi yozuvi',
    columns=[('Xodim', 'employee'), ('Yil', 'year'), ('Oy', 'month'), ('Hisoblangan', 'base'), ('Bonus', 'bonus'),
             ('Jarima', 'penalty'), ('Jami', 'total'), ("To'langan", 'paid')],
    fields=['bonus', 'penalty'], select_related=('employee',), allow_add=False, allow_detail=False,
)

urlpatterns = (
    employees.patterns() + teams.patterns() + shifts.patterns() + attendance.patterns()
    + payroll_records.patterns()
    + [
        path('ish-haqi/', views.payroll, name='payroll'),
        path('vazifalarim/', views.my_tasks, name='my_tasks'),
        path('vazifalarim/davomat/', views.my_checkin, name='my_checkin'),
    ]
)
