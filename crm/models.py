import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Client(models.Model):
    class Kind(models.TextChoices):
        INDIVIDUAL = 'individual', 'Jismoniy shaxs'
        LEGAL = 'legal', 'Yuridik shaxs'

    kind = models.CharField('Turi', max_length=12, choices=Kind.choices, default=Kind.INDIVIDUAL)
    name = models.CharField('F.I.Sh. / Kompaniya nomi', max_length=200)
    stir = models.CharField('STIR', max_length=20, blank=True)
    contact_person = models.CharField('Aloqa uchun shaxs', max_length=150, blank=True)
    phone = models.CharField('Telefon', max_length=30)
    email = models.EmailField('Email', blank=True)
    address = models.CharField('Manzil', max_length=255, blank=True)
    note = models.TextField('Izoh', blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name='Kabinet foydalanuvchisi', null=True,
                                blank=True, on_delete=models.SET_NULL, related_name='client_profile')
    created_at = models.DateTimeField('Qo\'shilgan', auto_now_add=True)

    class Meta:
        verbose_name = 'Mijoz'
        verbose_name_plural = 'Mijozlar'
        ordering = ['name']

    def __str__(self):
        return self.name

    def total_debt(self):
        """Mijozning umumiy qarzdorligi (bekor qilinmagan hisob-fakturalar bo'yicha)."""
        total = Decimal('0')
        for inv in self.invoices.exclude(status='cancelled'):
            total += inv.debt
        return total


class Contract(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Qoralama'
        ACTIVE = 'active', 'Amalda'
        EXPIRED = 'expired', 'Muddati tugagan'
        TERMINATED = 'terminated', 'Bekor qilingan'

    client = models.ForeignKey(Client, verbose_name='Mijoz', on_delete=models.PROTECT, related_name='contracts')
    number = models.CharField('Shartnoma raqami', max_length=40, unique=True)
    date = models.DateField('Sana', default=timezone.localdate)
    end_date = models.DateField('Amal qilish muddati (gacha)', null=True, blank=True)
    amount = models.DecimalField("Summa (so'm)", max_digits=14, decimal_places=2, default=0)
    status = models.CharField('Holat', max_length=12, choices=Status.choices, default=Status.ACTIVE)
    note = models.TextField('Izoh', blank=True)

    class Meta:
        verbose_name = 'Shartnoma'
        verbose_name_plural = 'Shartnomalar'
        ordering = ['-date']

    def __str__(self):
        return f'№{self.number} — {self.client}'

    @property
    def is_expired(self):
        return bool(self.end_date and self.end_date < datetime.date.today()
                    and self.status == self.Status.ACTIVE)


class Interaction(models.Model):
    class Channel(models.TextChoices):
        PHONE = 'phone', 'Telefon'
        VISIT = 'visit', 'Uchrashuv'
        EMAIL = 'email', 'Email'
        TELEGRAM = 'telegram', 'Telegram'
        OTHER = 'other', 'Boshqa'

    client = models.ForeignKey(Client, verbose_name='Mijoz', on_delete=models.CASCADE, related_name='interactions')
    date = models.DateField('Sana', default=timezone.localdate)
    channel = models.CharField('Aloqa kanali', max_length=10, choices=Channel.choices, default=Channel.PHONE)
    subject = models.CharField('Mavzu', max_length=200)
    text = models.TextField('Mazmuni', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Kiritgan', null=True, blank=True,
                                   on_delete=models.SET_NULL, editable=False)

    class Meta:
        verbose_name = 'Murojaat / muloqot'
        verbose_name_plural = 'Murojaatlar va muloqotlar'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.client}: {self.subject}'


class Lead(models.Model):
    """Ochiq saytdan kelgan ariza."""

    class Status(models.TextChoices):
        NEW = 'new', 'Yangi'
        CONTACTED = 'contacted', "Bog'lanildi"
        CONVERTED = 'converted', 'Mijozga aylandi'
        REJECTED = 'rejected', 'Rad etildi'

    name = models.CharField('Ismi', max_length=150)
    phone = models.CharField('Telefon', max_length=30)
    service = models.ForeignKey('orders.ServiceType', verbose_name='Xizmat', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='leads')
    address = models.CharField('Manzil', max_length=255, blank=True)
    message = models.TextField('Xabar', blank=True)
    status = models.CharField('Holat', max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField('Kelgan vaqt', auto_now_add=True)

    class Meta:
        verbose_name = 'Ariza'
        verbose_name_plural = 'Arizalar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.phone})'
