from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone


class Supplier(models.Model):
    name = models.CharField('Nomi', max_length=150)
    phone = models.CharField('Telefon', max_length=30, blank=True)
    address = models.CharField('Manzil', max_length=255, blank=True)
    note = models.CharField('Izoh', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Yetkazib beruvchi'
        verbose_name_plural = 'Yetkazib beruvchilar'
        ordering = ['name']

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    class Kind(models.TextChoices):
        CHEMICAL = 'chemical', 'Kimyoviy vosita'
        CONSUMABLE = 'consumable', 'Sarf materiali'
        EQUIPMENT = 'equipment', 'Uskuna'

    name = models.CharField('Nomi', max_length=150)
    kind = models.CharField('Turi', max_length=12, choices=Kind.choices, default=Kind.CONSUMABLE)
    unit = models.CharField('Birligi', max_length=20, default='dona', help_text='dona, litr, kg, paket ...')
    quantity = models.DecimalField('Qoldiq', max_digits=12, decimal_places=2, default=0, editable=False)
    min_quantity = models.DecimalField('Minimal qoldiq', max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField("Narxi (so'm)", max_digits=12, decimal_places=2, default=0, blank=True)
    is_active = models.BooleanField('Faol', default=True)

    class Meta:
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_low(self):
        return self.quantity <= self.min_quantity

    def stock_label(self):
        return 'Kam qolgan' if self.is_low else 'Yetarli'


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN = 'in', 'Kirim'
        OUT = 'out', 'Chiqim (berish)'
        RETURN = 'return', 'Qaytarish'
        ADJUST = 'adjust', 'Tuzatish (inventarizatsiya)'

    item = models.ForeignKey(InventoryItem, verbose_name='Mahsulot', on_delete=models.PROTECT,
                             related_name='movements')
    kind = models.CharField('Turi', max_length=8, choices=Kind.choices, default=Kind.IN)
    quantity = models.DecimalField('Miqdor', max_digits=12, decimal_places=2)
    date = models.DateField('Sana', default=timezone.localdate)
    facility = models.ForeignKey('facilities.Facility', verbose_name='Obyekt', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='stock_movements')
    employee = models.ForeignKey('hr.Employee', verbose_name='Xodim', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='stock_movements')
    supplier = models.ForeignKey(Supplier, verbose_name='Yetkazib beruvchi', null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='movements')
    note = models.CharField('Izoh', max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Kiritgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False, related_name='+')

    class Meta:
        verbose_name = 'Ombor harakati'
        verbose_name_plural = 'Kirim-chiqim'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.get_kind_display()}: {self.item} × {self.quantity}'

    @property
    def delta(self):
        """Qoldiqqa ta'siri (+/-)."""
        q = Decimal(str(self.quantity))
        return -q if self.kind == self.Kind.OUT else q

    def clean(self):
        if self.kind != self.Kind.ADJUST and self.quantity is not None and self.quantity <= 0:
            raise ValidationError({'quantity': "Miqdor noldan katta bo'lishi kerak."})
        if self.kind == self.Kind.OUT and self.item_id and self.quantity is not None and not self.pk:
            if self.quantity > self.item.quantity:
                raise ValidationError({'quantity': f'Omborda yetarli emas: qoldiq {self.item.quantity} {self.item.unit}.'})

    def save(self, *args, **kwargs):
        # Qoldiq faqat yangi harakat yaratilganda yangilanadi (harakatlar tahrirlanmaydi)
        creating = self.pk is None
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                InventoryItem.objects.filter(pk=self.item_id).update(quantity=F('quantity') + self.delta)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            InventoryItem.objects.filter(pk=self.item_id).update(quantity=F('quantity') - self.delta)
            return super().delete(*args, **kwargs)
