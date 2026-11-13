import calendar
import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ServiceType(models.Model):
    class Unit(models.TextChoices):
        M2 = 'm2', '1 m² uchun'
        HOUR = 'hour', '1 soat uchun'
        FIXED = 'fixed', 'Belgilangan narx'

    name = models.CharField('Nomi', max_length=150)
    description = models.TextField('Tavsif', blank=True)
    unit = models.CharField('Narx birligi', max_length=6, choices=Unit.choices, default=Unit.M2)
    price = models.DecimalField("Narx (so'm)", max_digits=12, decimal_places=2)
    icon = models.CharField('Ikonka (Bootstrap Icons nomi)', max_length=40, default='bi-stars', blank=True)
    is_active = models.BooleanField('Faol', default=True)

    class Meta:
        verbose_name = 'Xizmat turi'
        verbose_name_plural = 'Xizmat turlari'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def unit_short(self):
        return {'m2': 'm²', 'hour': 'soat', 'fixed': 'xizmat'}.get(self.unit, '')


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Yangi'
        CONFIRMED = 'confirmed', 'Tasdiqlangan'
        IN_PROGRESS = 'in_progress', 'Jarayonda'
        DONE = 'done', 'Bajarildi'
        CANCELLED = 'cancelled', 'Bekor qilindi'

    class Recurrence(models.TextChoices):
        NONE = 'none', 'Takrorlanmaydi'
        DAILY = 'daily', 'Har kuni'
        WEEKLY = 'weekly', 'Har hafta'
        MONTHLY = 'monthly', 'Har oy'

    number = models.CharField('Raqami', max_length=20, unique=True, null=True, blank=True, editable=False)
    client = models.ForeignKey('crm.Client', verbose_name='Mijoz', on_delete=models.PROTECT, related_name='orders')
    facility = models.ForeignKey('facilities.Facility', verbose_name='Obyekt', on_delete=models.PROTECT,
                                 related_name='orders')
    service = models.ForeignKey(ServiceType, verbose_name='Xizmat turi', on_delete=models.PROTECT,
                                related_name='orders')
    contract = models.ForeignKey('crm.Contract', verbose_name='Shartnoma', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='orders')
    team = models.ForeignKey('hr.Team', verbose_name='Brigada', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='orders')
    date = models.DateField('Sana', default=timezone.localdate)
    time = models.TimeField('Vaqt', default=datetime.time(9, 0))
    status = models.CharField('Holat', max_length=12, choices=Status.choices, default=Status.NEW)
    quantity = models.DecimalField('Miqdor (m² yoki soat)', max_digits=10, decimal_places=2, default=1,
                                   help_text="Narx birligi m² bo'lsa — maydon, soatbay bo'lsa — soat. "
                                             "Belgilangan narxda e'tiborga olinmaydi.")
    unit_price = models.DecimalField("Birlik narxi (so'm)", max_digits=12, decimal_places=2, default=0, blank=True,
                                     help_text="Bo'sh yoki 0 qoldirilsa, xizmat narxi olinadi.")
    total = models.DecimalField("Jami summa (so'm)", max_digits=14, decimal_places=2, default=0, editable=False)
    recurrence = models.CharField('Takrorlanishi', max_length=8, choices=Recurrence.choices,
                                  default=Recurrence.NONE)
    recurrence_end = models.DateField('Takrorlanish tugashi', null=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children',
                               editable=False)
    note = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Yaratgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False, related_name='+')
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)

    class Meta:
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'
        ordering = ['-date', '-time']

    def __str__(self):
        return f'{self.number or "Yangi"} — {self.client}'

    def clean(self):
        if self.client_id and self.facility_id and self.facility.client_id != self.client_id:
            raise ValidationError({'facility': 'Tanlangan obyekt bu mijozga tegishli emas.'})
        if self.recurrence_end and self.date and self.recurrence_end < self.date:
            raise ValidationError({'recurrence_end': "Takrorlanish tugashi buyurtma sanasidan oldin bo'lmasligi kerak."})

    def calc_total(self):
        price = Decimal(str(self.unit_price or 0))
        if self.service.unit == ServiceType.Unit.FIXED:
            total = price
        else:
            total = price * Decimal(str(self.quantity or 0))
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.service.price
        self.total = self.calc_total()
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f'B-{self.pk:06d}'
            super().save(update_fields=['number'])

    # ------------------------------------------------------------ takroriy buyurtmalar
    @staticmethod
    def _next_date(cur, rule):
        if rule == Order.Recurrence.DAILY:
            return cur + datetime.timedelta(days=1)
        if rule == Order.Recurrence.WEEKLY:
            return cur + datetime.timedelta(days=7)
        m = cur.month  # oylik
        y = cur.year + (1 if m == 12 else 0)
        m = 1 if m == 12 else m + 1
        return datetime.date(y, m, min(cur.day, calendar.monthrange(y, m)[1]))

    def generate_recurrences(self, horizon_days=60):
        """Takrorlanuvchi buyurtmadan kelgusi buyurtmalarni yaratadi. Yaratilgan sonini qaytaradi."""
        if self.recurrence == self.Recurrence.NONE or self.parent_id:
            return 0
        limit = timezone.localdate() + datetime.timedelta(days=horizon_days)
        if self.recurrence_end:
            limit = min(limit, self.recurrence_end)
        created = 0
        cur = self.date
        while True:
            cur = self._next_date(cur, self.recurrence)
            if cur > limit:
                break
            if not self.children.filter(date=cur).exists():
                Order.objects.create(
                    client=self.client, facility=self.facility, service=self.service, contract=self.contract,
                    team=self.team, date=cur, time=self.time, status=self.Status.NEW, quantity=self.quantity,
                    unit_price=self.unit_price, recurrence=self.Recurrence.NONE, parent=self, note=self.note,
                    created_by=self.created_by)
                created += 1
        return created
