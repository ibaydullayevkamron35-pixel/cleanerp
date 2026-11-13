import datetime

from django.db import models


class Facility(models.Model):
    class Kind(models.TextChoices):
        OFFICE = 'office', 'Ofis'
        HOME = 'home', 'Turar joy / uy'
        MALL = 'mall', 'Savdo markazi'
        SCHOOL = 'school', 'Maktab / bog\'cha'
        HOSPITAL = 'hospital', 'Shifoxona'
        HOTEL = 'hotel', 'Mehmonxona'
        WAREHOUSE = 'warehouse', 'Ombor / ishlab chiqarish'
        OTHER = 'other', 'Boshqa'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Faol'
        INACTIVE = 'inactive', 'Nofaol'

    client = models.ForeignKey('crm.Client', verbose_name='Mijoz', on_delete=models.PROTECT,
                               related_name='facilities')
    name = models.CharField('Nomi', max_length=200)
    kind = models.CharField('Turi', max_length=12, choices=Kind.choices, default=Kind.OFFICE)
    address = models.CharField('Manzil', max_length=255)
    area = models.DecimalField('Umumiy maydon (m²)', max_digits=10, decimal_places=2, default=0)
    floors = models.PositiveSmallIntegerField('Qavatlar soni', default=1)
    requirements = models.TextField('Tozalash talablari', blank=True)
    instructions = models.TextField("Maxsus ko'rsatmalar", blank=True)
    status = models.CharField('Holat', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    teams = models.ManyToManyField('hr.Team', verbose_name='Biriktirilgan brigadalar', blank=True,
                                   related_name='facilities')
    employees = models.ManyToManyField('hr.Employee', verbose_name='Biriktirilgan xodimlar', blank=True,
                                       related_name='facilities')
    created_at = models.DateTimeField("Qo'shilgan", auto_now_add=True)

    class Meta:
        verbose_name = 'Obyekt'
        verbose_name_plural = 'Obyektlar'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.client})'


class Zone(models.Model):
    class CleaningType(models.TextChoices):
        DAILY = 'daily', 'Kundalik'
        GENERAL = 'general', 'General'
        DEEP = 'deep', 'Chuqur tozalash'
        DISINFECTION = 'disinfection', 'Dezinfeksiya'

    facility = models.ForeignKey(Facility, verbose_name='Obyekt', on_delete=models.CASCADE, related_name='zones')
    name = models.CharField('Xona / zona nomi', max_length=150)
    area = models.DecimalField('Maydon (m²)', max_digits=9, decimal_places=2, default=0)
    cleaning_type = models.CharField('Tozalash turi', max_length=14, choices=CleaningType.choices,
                                     default=CleaningType.DAILY)

    class Meta:
        verbose_name = 'Zona'
        verbose_name_plural = 'Zonalar'
        ordering = ['facility', 'name']

    def __str__(self):
        return f'{self.name} — {self.facility.name}'


class CleaningSchedule(models.Model):
    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Kundalik'
        WEEKLY = 'weekly', 'Haftalik'
        MONTHLY = 'monthly', 'Oylik'

    WEEKDAYS = [(0, 'Dushanba'), (1, 'Seshanba'), (2, 'Chorshanba'), (3, 'Payshanba'),
                (4, 'Juma'), (5, 'Shanba'), (6, 'Yakshanba')]

    facility = models.ForeignKey(Facility, verbose_name='Obyekt', on_delete=models.CASCADE,
                                 related_name='schedules')
    service = models.ForeignKey('orders.ServiceType', verbose_name='Xizmat', on_delete=models.PROTECT)
    frequency = models.CharField('Davriylik', max_length=10, choices=Frequency.choices,
                                 default=Frequency.DAILY)
    weekday = models.PositiveSmallIntegerField('Hafta kuni (haftalik uchun)', choices=WEEKDAYS, null=True,
                                               blank=True)
    month_day = models.PositiveSmallIntegerField('Oy kuni (oylik uchun, 1-28)', null=True, blank=True)
    time = models.TimeField('Vaqti', default=datetime.time(9, 0))
    is_active = models.BooleanField('Faol', default=True)
    note = models.CharField('Izoh', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Tozalash jadvali'
        verbose_name_plural = 'Tozalash jadvallari'
        ordering = ['facility', 'frequency']

    def __str__(self):
        return f'{self.facility.name}: {self.get_frequency_display()} — {self.service}'

    @property
    def when(self):
        if self.frequency == self.Frequency.WEEKLY and self.weekday is not None:
            return f'{dict(self.WEEKDAYS)[self.weekday]}, {self.time:%H:%M}'
        if self.frequency == self.Frequency.MONTHLY and self.month_day:
            return f'Har oyning {self.month_day}-kuni, {self.time:%H:%M}'
        return f'Har kuni, {self.time:%H:%M}'
