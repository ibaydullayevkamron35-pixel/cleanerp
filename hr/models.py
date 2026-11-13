import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Employee(models.Model):
    class PayType(models.TextChoices):
        FIXED = 'fixed', 'Belgilangan oylik'
        HOURLY = 'hourly', 'Soatbay'
        VOLUME = 'volume', 'Bajarilgan ish hajmiga qarab (1 m² uchun)'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Ishlayapti'
        VACATION = 'vacation', 'Ta\'tilda'
        DISMISSED = 'dismissed', 'Bo\'shatilgan'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name='Tizimga kirish hisobi', null=True,
                                blank=True, on_delete=models.SET_NULL, related_name='employee_profile')
    full_name = models.CharField('F.I.Sh.', max_length=200)
    position = models.CharField('Lavozimi', max_length=120, default='Tozalovchi')
    phone = models.CharField('Telefon', max_length=30, blank=True)
    hire_date = models.DateField('Ishga qabul sanasi', default=timezone.localdate)
    pay_type = models.CharField('Maosh turi', max_length=8, choices=PayType.choices, default=PayType.FIXED)
    pay_rate = models.DecimalField("Maosh / stavka (so'm)", max_digits=12, decimal_places=2, default=0,
                                   help_text='Oylik summa, soatlik stavka yoki 1 m² uchun haq.')
    team = models.ForeignKey('Team', verbose_name='Brigada', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='members')
    status = models.CharField('Holat', max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = 'Xodim'
        verbose_name_plural = 'Xodimlar'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Team(models.Model):
    name = models.CharField('Brigada nomi', max_length=120)
    foreman = models.ForeignKey(Employee, verbose_name='Brigadir', null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='led_teams')
    note = models.CharField('Izoh', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Brigada'
        verbose_name_plural = 'Brigadalar'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.exclude(status=Employee.Status.DISMISSED).count()


class Shift(models.Model):
    """Xodimni obyekt va buyurtmaga biriktirish — kunlik/haftalik ish jadvali."""
    employee = models.ForeignKey(Employee, verbose_name='Xodim', on_delete=models.CASCADE, related_name='shifts')
    facility = models.ForeignKey('facilities.Facility', verbose_name='Obyekt', on_delete=models.PROTECT,
                                 related_name='shifts')
    order = models.ForeignKey('orders.Order', verbose_name='Buyurtma', null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='shifts')
    date = models.DateField('Sana', default=timezone.localdate)
    start_time = models.TimeField('Boshlanishi', default=datetime.time(9, 0))
    end_time = models.TimeField('Tugashi', default=datetime.time(18, 0))
    note = models.CharField('Izoh', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Smena'
        verbose_name_plural = 'Ish jadvali (smenalar)'
        ordering = ['-date', 'start_time']

    def __str__(self):
        return f'{self.employee} — {self.facility.name} ({self.date:%d.%m.%Y})'


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Keldi'
        LATE = 'late', 'Kechikdi'
        ABSENT = 'absent', 'Kelmadi'
        LEAVE = 'leave', 'Ruxsat / ta\'til'

    employee = models.ForeignKey(Employee, verbose_name='Xodim', on_delete=models.CASCADE,
                                 related_name='attendance')
    date = models.DateField('Sana', default=timezone.localdate)
    facility = models.ForeignKey('facilities.Facility', verbose_name='Obyekt', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='attendance')
    check_in = models.TimeField('Kelgan vaqti', null=True, blank=True)
    check_out = models.TimeField('Ketgan vaqti', null=True, blank=True)
    status = models.CharField('Holat', max_length=8, choices=Status.choices, default=Status.PRESENT)
    note = models.CharField('Izoh', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Davomat'
        verbose_name_plural = 'Davomat'
        ordering = ['-date', 'employee__full_name']
        constraints = [models.UniqueConstraint(fields=['employee', 'date'], name='uniq_attendance_employee_date')]

    def __str__(self):
        return f'{self.employee} — {self.date:%d.%m.%Y}'

    def save(self, *args, **kwargs):
        start = getattr(settings, 'WORK_START', None)
        if self.status == self.Status.PRESENT and self.check_in and start and self.check_in > start:
            self.status = self.Status.LATE
        super().save(*args, **kwargs)

    @property
    def hours(self):
        if self.check_in and self.check_out and self.check_out > self.check_in:
            a = datetime.datetime.combine(self.date, self.check_in)
            b = datetime.datetime.combine(self.date, self.check_out)
            return (Decimal((b - a).seconds) / Decimal(3600)).quantize(Decimal('0.01'))
        return Decimal('0')


class PayrollRecord(models.Model):
    employee = models.ForeignKey(Employee, verbose_name='Xodim', on_delete=models.CASCADE, related_name='payroll')
    year = models.PositiveSmallIntegerField('Yil')
    month = models.PositiveSmallIntegerField('Oy')
    base = models.DecimalField("Hisoblangan (so'm)", max_digits=14, decimal_places=2, default=0)
    bonus = models.DecimalField("Bonus (so'm)", max_digits=14, decimal_places=2, default=0)
    penalty = models.DecimalField("Jarima (so'm)", max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField("Jami (so'm)", max_digits=14, decimal_places=2, default=0, editable=False)
    paid = models.BooleanField("To'langan", default=False)
    paid_date = models.DateField("To'langan sana", null=True, blank=True)

    class Meta:
        verbose_name = 'Ish haqi yozuvi'
        verbose_name_plural = 'Ish haqi'
        ordering = ['-year', '-month', 'employee__full_name']
        constraints = [models.UniqueConstraint(fields=['employee', 'year', 'month'], name='uniq_payroll_period')]

    def __str__(self):
        return f'{self.employee} — {self.month:02d}.{self.year}'

    def save(self, *args, **kwargs):
        self.total = (self.base or 0) + (self.bonus or 0) - (self.penalty or 0)
        super().save(*args, **kwargs)
