from django.db.models import Q

from accounts.models import User
from core.forms import BootstrapModelForm

from .models import Employee


class EmployeeForm(BootstrapModelForm):
    class Meta:
        model = Employee
        fields = ['full_name', 'user', 'position', 'phone', 'hire_date', 'pay_type', 'pay_rate', 'team', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cond = Q(employee_profile__isnull=True)
        if self.instance.pk:
            cond |= Q(employee_profile=self.instance)
        self.fields['user'].queryset = User.objects.filter(role__in=['cleaner', 'foreman']).filter(cond)
        self.fields['user'].help_text = ("Xodim tizimga kirishi uchun: avval «Foydalanuvchilar» bo'limida "
                                         "'Tozalovchi' yoki 'Brigadir' rolida hisob yarating.")
