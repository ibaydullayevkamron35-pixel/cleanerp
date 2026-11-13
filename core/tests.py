"""CleanERP smoke va biznes-mantiq testlari.  Ishga tushirish:  python manage.py test"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, get_resolver, reverse
from django.utils import timezone

from accounts.models import User
from crm.models import Client
from facilities.models import Facility
from finance.models import Invoice, Payment
from inventory.models import InventoryItem, StockMovement
from orders.models import Order, ServiceType


def make_basics():
    client = Client.objects.create(name='Test MChJ', phone='+998901112233', kind='legal')
    facility = Facility.objects.create(client=client, name='Ofis', address='Toshkent', area=Decimal('100'))
    service = ServiceType.objects.create(name='Kundalik', unit='m2', price=Decimal('3000'))
    return client, facility, service


class BusinessLogicTests(TestCase):
    def test_order_total_and_number(self):
        client, facility, service = make_basics()
        o = Order.objects.create(client=client, facility=facility, service=service, quantity=Decimal('100'))
        self.assertEqual(o.total, Decimal('300000.00'))
        self.assertEqual(o.number, f'B-{o.pk:06d}')

    def test_fixed_price_ignores_quantity(self):
        client, facility, _ = make_basics()
        fixed = ServiceType.objects.create(name='Maxsus', unit='fixed', price=Decimal('500000'))
        o = Order.objects.create(client=client, facility=facility, service=fixed, quantity=Decimal('7'))
        self.assertEqual(o.total, Decimal('500000.00'))

    def test_facility_must_belong_to_client(self):
        client, facility, service = make_basics()
        other = Client.objects.create(name='Boshqa', phone='1')
        o = Order(client=other, facility=facility, service=service, quantity=1)
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_recurrence_generation_is_idempotent(self):
        client, facility, service = make_basics()
        today = timezone.localdate()
        o = Order.objects.create(client=client, facility=facility, service=service, quantity=1, date=today,
                                 recurrence='weekly', recurrence_end=today + datetime.timedelta(days=21))
        self.assertEqual(o.generate_recurrences(), 3)
        self.assertEqual(o.generate_recurrences(), 0)

    def test_invoice_status_follows_payments(self):
        client, facility, service = make_basics()
        o = Order.objects.create(client=client, facility=facility, service=service, quantity=100)
        inv = Invoice.objects.create(order=o, client=client, amount=o.total)
        self.assertEqual(inv.status, 'unpaid')
        p = Payment.objects.create(invoice=inv, amount=Decimal('100000'))
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'partial')
        self.assertEqual(inv.debt, Decimal('200000.00'))
        Payment.objects.create(invoice=inv, amount=Decimal('200000'))
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'paid')
        p.delete()
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'partial')

    def test_overpayment_rejected(self):
        client, facility, service = make_basics()
        o = Order.objects.create(client=client, facility=facility, service=service, quantity=1)
        inv = Invoice.objects.create(order=o, client=client, amount=o.total)
        with self.assertRaises(ValidationError):
            Payment(invoice=inv, amount=o.total + 1).full_clean()

    def test_stock_movements_update_balance(self):
        item = InventoryItem.objects.create(name='Vosita', unit='litr', min_quantity=5)
        StockMovement.objects.create(item=item, kind='in', quantity=10)
        StockMovement.objects.create(item=item, kind='out', quantity=4)
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal('6.00'))
        mv = StockMovement.objects.create(item=item, kind='out', quantity=3)
        item.refresh_from_db()
        self.assertTrue(item.is_low)
        mv.delete()
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal('6.00'))

    def test_cannot_issue_more_than_stock(self):
        item = InventoryItem.objects.create(name='Vosita', unit='litr')
        StockMovement.objects.create(item=item, kind='in', quantity=2)
        with self.assertRaises(ValidationError):
            StockMovement(item=item, kind='out', quantity=5).full_clean()


class AccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def login(self, username):
        self.client.logout()
        self.assertTrue(self.client.login(username=username, password='demo12345'))

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse('clients_list'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/kirish/', r['Location'])

    def test_public_pages_open(self):
        for name in ('landing', 'services_public', 'login', 'register'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_lead_form_creates_lead(self):
        from crm.models import Lead
        before = Lead.objects.count()
        r = self.client.post(reverse('landing'), {'name': 'Ali', 'phone': '+998901234567'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Lead.objects.count(), before + 1)

    def test_role_restrictions(self):
        self.login('tozalovchi')
        self.assertEqual(self.client.get(reverse('clients_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('invoices_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('my_tasks')).status_code, 200)
        self.login('mijoz')
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 403)
        self.assertEqual(self.client.get(reverse('cabinet')).status_code, 200)
        self.login('omborchi')
        self.assertEqual(self.client.get(reverse('inventory_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('payments_list')).status_code, 403)
        self.login('buxgalter')
        self.assertEqual(self.client.get(reverse('payments_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('inventory_list')).status_code, 403)

    def test_client_sees_only_own_invoice_pdf(self):
        self.login('mijoz')
        mine = Invoice.objects.filter(client__user__username='mijoz').first()
        other = Invoice.objects.exclude(client__user__username='mijoz').first()
        if mine:
            self.assertEqual(self.client.get(reverse('invoices_pdf', args=[mine.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('invoices_pdf', args=[other.pk])).status_code, 403)

    def test_all_list_and_detail_pages_open_for_admin(self):
        """Barcha ro'yxat/detail/tahrirlash sahifalari xatosiz ochilishi kerak."""
        self.login('admin')
        names = {p.name for p in _flatten(get_resolver().url_patterns) if p.name}
        checked = 0
        for name in sorted(names):
            if not (name.endswith('_list') or name in ('dashboard', 'reports', 'payroll', 'ratings', 'my_tasks',
                                                         'inventory_count', 'inspections_add', 'profile')):
                continue
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, f'{name} -> {r.status_code}')
            checked += 1
        for name, model_pk in _first_pks().items():
            for suffix in ('detail', 'edit'):
                try:
                    url = reverse(f'{name}_{suffix}', args=[model_pk])
                except NoReverseMatch:
                    continue
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200, f'{name}_{suffix} -> {r.status_code}')
                checked += 1
        self.assertGreater(checked, 40)

    def test_reports_and_exports(self):
        self.login('admin')
        for code in ('orders', 'finance', 'profit', 'debts', 'inventory', 'attendance', 'quality'):
            self.assertEqual(self.client.get(reverse('reports'), {'type': code, 'period': 'year'}).status_code, 200, code)
            r = self.client.get(reverse('reports'), {'type': code, 'period': 'year', 'export': 'xlsx'})
            self.assertEqual(r.status_code, 200, code)
            r = self.client.get(reverse('reports'), {'type': code, 'period': 'year', 'export': 'pdf'})
            self.assertEqual(r.status_code, 200, code)
        self.assertEqual(self.client.get(reverse('clients_export')).status_code, 200)

    def test_order_status_flow_and_invoice(self):
        self.login('menejer')
        order = Order.objects.filter(status='new').first()
        r = self.client.post(reverse('orders_status', args=[order.pk, 'confirmed']))
        self.assertEqual(r.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

    def test_protected_delete_shows_message_not_error(self):
        self.login('admin')
        c = Client.objects.filter(orders__isnull=False).first()
        r = self.client.post(reverse('clients_delete', args=[c.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Client.objects.filter(pk=c.pk).exists())

    def test_registration_creates_client_and_logs_in(self):
        r = self.client.post(reverse('register'), {
            'kind': 'individual', 'name': 'Yangi Mijoz', 'phone': '+998901112233', 'username': 'yangimijoz',
            'password1': 'Kuchli-Parol-2026', 'password2': 'Kuchli-Parol-2026'})
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username='yangimijoz')
        self.assertEqual(u.role, 'client')
        self.assertTrue(Client.objects.filter(user=u).exists())
        self.assertEqual(self.client.get(reverse('cabinet')).status_code, 200)


def _flatten(patterns):
    for p in patterns:
        if hasattr(p, 'url_patterns'):
            if getattr(p, 'app_name', None) == 'admin':
                continue  # Django admin nomlari (app_list va b.) bu testga tegishli emas
            yield from _flatten(p.url_patterns)
        else:
            yield p


def _first_pks():
    from crm.models import Client, Contract, Lead
    from facilities.models import Facility
    from hr.models import Employee, Team
    from inventory.models import InventoryItem
    from quality.models import Complaint, Inspection
    pairs = {'clients': Client, 'contracts': Contract, 'leads': Lead, 'facilities': Facility, 'orders': Order,
             'invoices': Invoice, 'employees': Employee, 'teams': Team, 'inventory': InventoryItem,
             'inspections': Inspection, 'complaints': Complaint}
    return {k: m.objects.first().pk for k, m in pairs.items() if m.objects.exists()}
