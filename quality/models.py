from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Inspection(models.Model):
    facility = models.ForeignKey('facilities.Facility', verbose_name='Obyekt', on_delete=models.PROTECT,
                                 related_name='inspections')
    order = models.ForeignKey('orders.Order', verbose_name='Buyurtma', null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='inspections')
    inspector = models.ForeignKey('hr.Employee', verbose_name='Tekshiruvchi', null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name='inspections')
    date = models.DateField('Sana', default=timezone.localdate)
    score = models.DecimalField('Umumiy ball (%)', max_digits=5, decimal_places=1, default=0, editable=False)
    note = models.TextField('Izoh', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Kiritgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False, related_name='+')

    class Meta:
        verbose_name = 'Tekshiruv'
        verbose_name_plural = 'Tekshiruvlar'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.facility.name} — {self.date:%d.%m.%Y}'

    def recalc(self):
        scores = list(self.items.values_list('score', flat=True))
        if scores:
            self.score = (Decimal(sum(scores)) / Decimal(len(scores)) / Decimal(5) * 100).quantize(Decimal('0.1'))
        else:
            self.score = Decimal('0')
        Inspection.objects.filter(pk=self.pk).update(score=self.score)


class InspectionItem(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='items')
    zone = models.ForeignKey('facilities.Zone', verbose_name='Zona', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='+')
    criterion = models.CharField('Mezon', max_length=200)
    score = models.PositiveSmallIntegerField('Ball (1-5)', default=5,
                                             validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.CharField('Izoh', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Tekshiruv mezoni'
        verbose_name_plural = 'Tekshiruv mezonlari'
        ordering = ['id']

    def __str__(self):
        return f'{self.criterion}: {self.score}'


class Complaint(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Yangi'
        IN_PROGRESS = 'in_progress', "Ko'rib chiqilmoqda"
        RESOLVED = 'resolved', 'Hal qilindi'
        CLOSED = 'closed', 'Yopildi'

    client = models.ForeignKey('crm.Client', verbose_name='Mijoz', on_delete=models.PROTECT,
                               related_name='complaints')
    order = models.ForeignKey('orders.Order', verbose_name='Buyurtma', null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='complaints')
    subject = models.CharField('Mavzu', max_length=200)
    content = models.TextField('Mazmuni')
    date = models.DateField('Sana', default=timezone.localdate)
    status = models.CharField('Holat', max_length=12, choices=Status.choices, default=Status.NEW)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Mas'ul", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='assigned_complaints',
                                 limit_choices_to={'role__in': ['admin', 'manager', 'foreman']})
    resolution = models.TextField('Hal qilish natijasi', blank=True)

    class Meta:
        verbose_name = 'Shikoyat'
        verbose_name_plural = 'Shikoyatlar'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.subject} ({self.client})'


class Review(models.Model):
    order = models.OneToOneField('orders.Order', verbose_name='Buyurtma', on_delete=models.CASCADE,
                                 related_name='review')
    client = models.ForeignKey('crm.Client', verbose_name='Mijoz', on_delete=models.CASCADE,
                               related_name='reviews')
    rating = models.PositiveSmallIntegerField('Ball (1-5)', validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField('Izoh', blank=True)
    date = models.DateField('Sana', default=timezone.localdate)

    class Meta:
        verbose_name = 'Baho'
        verbose_name_plural = 'Baholar'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.order.number}: {self.rating}/5'
