import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = 'unpaid', "To'lanmagan"
        PARTIAL = 'partial', "Qisman to'langan"
        PAID = 'paid', "To'langan"
        CANCELLED = 'cancelled', 'Bekor qilingan'

    number = models.CharField('Raqami', max_length=20, unique=True, null=True, blank=True, editable=False)
    order = models.ForeignKey('orders.Order', verbose_name='Buyurtma', null=True, blank=True,
                              on_delete=models.PROTECT, related_name='invoices')
    client = models.ForeignKey('crm.Client', verbose_name='Mijoz', on_delete=models.PROTECT,
                               related_name='invoices')
    date = models.DateField('Sana', default=timezone.localdate)
    due_date = models.DateField("To'lash muddati", null=True, blank=True)
    amount = models.DecimalField("Summa (so'm)", max_digits=14, decimal_places=2)
    status = models.CharField('Holat', max_length=10, choices=Status.choices, default=Status.UNPAID)
    note = models.CharField('Izoh', max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Yaratgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False, related_name='+')

    class Meta:
        verbose_name = 'Hisob-faktura'
        verbose_name_plural = 'Hisob-fakturalar'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.number or "Yangi"} — {self.client}'

    def clean(self):
        if self.order_id and self.client_id and self.order.client_id != self.client_id:
            raise ValidationError({'order': 'Buyurtma boshqa mijozga tegishli.'})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f'H-{self.pk:06d}'
            super().save(update_fields=['number'])
        if self.status != self.Status.CANCELLED:
            self.refresh_status()

    @property
    def paid_amount(self):
        return self.payments.aggregate(s=Sum('amount'))['s'] or Decimal('0')

    @property
    def debt(self):
        if self.status == self.Status.CANCELLED:
            return Decimal('0')
        return max(self.amount - self.paid_amount, Decimal('0'))

    @property
    def is_overdue(self):
        return bool(self.due_date and self.due_date < datetime.date.today()
                    and self.status in (self.Status.UNPAID, self.Status.PARTIAL))

    def refresh_status(self):
        if self.status == self.Status.CANCELLED:
            return
        paid = self.paid_amount
        if paid >= self.amount and self.amount > 0:
            new = self.Status.PAID
        elif paid > 0:
            new = self.Status.PARTIAL
        else:
            new = self.Status.UNPAID
        if new != self.status:
            self.status = new
            Invoice.objects.filter(pk=self.pk).update(status=new)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Naqd pul'
        CARD = 'card', 'Plastik karta'
        TRANSFER = 'transfer', "Bank o'tkazmasi"

    invoice = models.ForeignKey(Invoice, verbose_name='Hisob-faktura', on_delete=models.PROTECT,
                                related_name='payments')
    date = models.DateField('Sana', default=timezone.localdate)
    amount = models.DecimalField("Summa (so'm)", max_digits=14, decimal_places=2)
    method = models.CharField("To'lov usuli", max_length=10, choices=Method.choices, default=Method.CASH)
    note = models.CharField('Izoh', max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Kiritgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False, related_name='+')

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.invoice} — {self.amount}'

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': "Summa noldan katta bo'lishi kerak."})
        if self.invoice_id and self.amount is not None:
            if self.invoice.status == Invoice.Status.CANCELLED:
                raise ValidationError({'invoice': 'Bekor qilingan hisob-fakturaga to\'lov qabul qilinmaydi.'})
            allowed = self.invoice.amount - self.invoice.paid_amount
            if self.pk:
                allowed += Payment.objects.filter(pk=self.pk).values_list('amount', flat=True).first() or 0
            if self.amount > allowed:
                raise ValidationError({'amount': f"To'lov summasi qarzdan oshib ketdi (qarz: {allowed})."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.refresh_status()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        result = super().delete(*args, **kwargs)
        invoice.refresh_status()
        return result


class Expense(models.Model):
    class Category(models.TextChoices):
        SALARY = 'salary', 'Ish haqi'
        MATERIALS = 'materials', 'Materiallar'
        TRANSPORT = 'transport', 'Transport'
        RENT = 'rent', 'Ijara / kommunal'
        OTHER = 'other', 'Boshqa'

    category = models.CharField('Turi', max_length=10, choices=Category.choices, default=Category.OTHER)
    amount = models.DecimalField("Summa (so'm)", max_digits=14, decimal_places=2)
    date = models.DateField('Sana', default=timezone.localdate)
    facility = models.ForeignKey('facilities.Facility', verbose_name='Obyekt', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='expenses')
    note = models.CharField('Izoh', max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Kiritgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False, related_name='+')

    class Meta:
        verbose_name = 'Xarajat'
        verbose_name_plural = 'Xarajatlar'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.get_category_display()} — {self.amount}'
