"""Dashboard bugun, shu hafta, shu oy va shu yil uchun nolga to'lib qolmasligi uchun demo yozuvlar qo'shadi.

    python manage.py fill_dashboard

Har bir davr (bugun, hafta, oy) uchun buyurtma, xarajat va to'lov yetarli bo'lsa, hech narsa yaratmaydi.
Mavjud yozuvlarni o'zgartirmaydi va o'chirmaydi, shuning uchun uni istalgan vaqtda qayta ishga tushirish xavfsiz.
Yil davri oy davrini o'z ichiga oladi, shuning uchun alohida to'ldirilmaydi.
"""
import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from facilities.models import Facility
from finance.models import Expense, Invoice, Payment
from hr.models import Team
from orders.models import Order, ServiceType

NOTE = 'Demo'
# davr: (buyurtma, xarajat, to'lov) kamida nechta bo'lishi kerak
NEED = {'today': (5, 1, 2), 'week': (8, 3, 4), 'month': (12, 6, 6)}
EXPENSE_KINDS = ['materials', 'transport', 'other', 'materials', 'transport', 'rent']


class Command(BaseCommand):
    help = "Dashboard uchun bugungi, haftalik va oylik demo ma'lumotlarni to'ldiradi."

    @transaction.atomic
    def handle(self, *args, **opts):
        today = timezone.localdate()
        self.today = today
        self.rnd = random.Random(today.toordinal())
        self.admin = User.objects.filter(role='admin').order_by('pk').first()
        self.facilities = list(Facility.objects.filter(status='active').select_related('client'))
        self.services = list(ServiceType.objects.filter(is_active=True))
        self.teams = list(Team.objects.all())
        if not self.facilities or not self.services:
            self.stdout.write(self.style.WARNING("Obyekt yoki xizmat yo'q. Avval seed_demo ni ishga tushiring."))
            return

        starts = {
            'today': today,
            'week': today - datetime.timedelta(days=today.weekday()),
            'month': today.replace(day=1),
        }
        made = {'order': 0, 'expense': 0, 'payment': 0}
        for period in ('today', 'week', 'month'):
            start = starts[period]
            need_o, need_e, need_p = NEED[period]

            have = Order.objects.filter(date__range=(start, today)).exclude(status='cancelled').count()
            for _ in range(max(need_o - have, 0)):
                self.make_order(self.rand_date(start), status=self.rnd.choice(
                    ['done', 'done', 'confirmed', 'in_progress', 'new']))
                made['order'] += 1

            have = Payment.objects.filter(date__range=(start, today)).count()
            for _ in range(max(need_p - have, 0)):
                self.make_paid_order(self.rand_date(start))
                made['payment'] += 1

            have = Expense.objects.filter(date__range=(start, today)).count()
            for i in range(max(need_e - have, 0)):
                self.make_expense(self.rand_date(start), period, i)
                made['expense'] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: buyurtma +{made['order']}, to'lov +{made['payment']}, xarajat +{made['expense']}."))

    # ------------------------------------------------------------------ yordamchilar
    def rand_date(self, start):
        return start + datetime.timedelta(days=self.rnd.randint(0, (self.today - start).days))

    def make_order(self, date, status, big=False):
        f = self.rnd.choice(self.facilities)
        s = self.rnd.choice(self.services)
        if s.unit == 'm2':
            qty = Decimal(self.rnd.randint(250, 320) if big else self.rnd.randint(60, 300))
        else:
            qty = Decimal(self.rnd.randint(2, 8))
        return Order.objects.create(
            client=f.client, facility=f, service=s, team=self.rnd.choice(self.teams) if self.teams else None,
            date=date, time=datetime.time(self.rnd.choice([8, 9, 10, 11, 13, 14, 15]), 0), status=status,
            quantity=qty, note=NOTE, created_by=self.admin)

    def make_paid_order(self, date):
        """Bajarilgan buyurtma, uning hisob-fakturasi va to'liq to'lovi."""
        o = self.make_order(date, 'done', big=True)
        inv = Invoice.objects.create(order=o, client=o.client, amount=o.total, date=date,
                                     due_date=date + datetime.timedelta(days=7), note=NOTE, created_by=self.admin)
        Payment.objects.create(invoice=inv, date=date, amount=o.total, method='transfer', note=NOTE,
                               created_by=self.admin)

    def make_expense(self, date, period, i):
        cat = EXPENSE_KINDS[i % len(EXPENSE_KINDS)]
        # bugun va hafta uchun kichik summalar, oy uchun kattaroq (foyda manfiy bo'lib ketmasligi uchun)
        amount = self.rnd.randrange(120_000, 350_000, 10_000) if period != 'month' else \
            self.rnd.randrange(400_000, 1_400_000, 50_000)
        Expense.objects.create(
            category=cat, amount=Decimal(amount), date=date,
            facility=self.rnd.choice(self.facilities) if cat != 'rent' else None,
            note=f'{NOTE}: {dict(Expense.Category.choices)[cat].lower()}', created_by=self.admin)
