"""Ko'p hajmli fake ma'lumotlar: mavjud ma'lumotlar ustiga qo'shiladi (seed_demo dan keyin ham ishlaydi).

    python manage.py seed_fake               # standart hajm
    python manage.py seed_fake --scale 2     # ikki baravar ko'p
    python manage.py seed_fake --seed 7      # boshqa tasodifiy to'plam

Yangi foydalanuvchilar paroli: demo12345
"""
import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from crm.models import Client, Contract, Interaction, Lead
from facilities.models import CleaningSchedule, Facility, Zone
from finance.models import Expense, Invoice, Payment
from hr.models import Attendance, Employee, PayrollRecord, Shift, Team
from hr.views import calc_base
from inventory.models import InventoryItem, StockMovement, Supplier
from orders.models import Order, ServiceType
from quality.models import Complaint, Inspection, InspectionItem, Review

PASSWORD = 'demo12345'

MALE = ['Aziz', 'Bekzod', 'Davron', 'Eldor', 'Farrux', 'G\'ayrat', 'Husan', 'Islom', 'Jamshid', 'Kamol', 'Laziz',
        'Mansur', 'Nodir', 'Oybek', 'Po\'lat', 'Rustam', 'Sanjar', 'Temur', 'Ulug\'bek', 'Vohid', 'Xurshid', 'Yusuf',
        'Zafar', 'Shoxrux', 'Abror', 'Behruz', 'Diyor', 'Javohir', 'Muhammadali', 'Sardor']
FEMALE = ['Aziza', 'Barno', 'Dilfuza', 'Feruza', 'Gulchehra', 'Hilola', 'Iroda', 'Kamola', 'Lobar', 'Madina',
          'Nargiza', 'Oydin', 'Robiya', 'Sabina', 'Tamara', 'Umida', 'Vasila', 'Xadicha', 'Yulduz', 'Zuhra',
          'Shahnoza', 'Charos', 'Muxlisa', 'Nilufar', 'Sevinch', 'Dildora', 'Maftuna', 'Mohira']
SURNAMES = ['Abdullayev', 'Bakirov', 'Davletov', 'Ergashev', 'Fayzullayev', 'G\'aniyev', 'Hamidov', 'Ismoilov',
            'Jo\'rayev', 'Karimov', 'Latipov', 'Mahmudov', 'Nurmatov', 'Olimov', 'Po\'latov', 'Rahimov', 'Sobirov',
            'Toshmatov', 'Usmonov', 'Valiyev', 'Xolmatov', 'Yo\'ldoshev', 'Zokirov', 'Qodirov', 'Sharipov',
            'Normatov', 'Tursunov', 'Haydarov', 'Mirzayev', 'Aliyev']
DISTRICTS = ['Chilonzor', 'Yunusobod', 'Mirzo Ulug\'bek', 'Shayxontohur', 'Yakkasaroy', 'Mirobod', 'Olmazor',
             'Sergeli', 'Uchtepa', 'Bektemir', 'Yashnobod', 'Yangihayot']
STREETS = ['Amir Temur', 'Bunyodkor', 'Shota Rustaveli', 'Mustaqillik', 'Navoiy', 'Bobur', 'Labzak', 'Qatortol',
           'Farg\'ona yo\'li', 'Beruniy', 'Muqimiy', 'Nukus', 'Taras Shevchenko', 'Oybek', 'Kichik halqa yo\'li']
COMPANY_WORDS = ['Smart', 'Mega', 'Silk Road', 'Sharq', 'Grand', 'Nur', 'Oltin', 'Yangi Asr', 'Turon', 'Samarqand',
                 'Inno', 'Asia', 'Green', 'Baraka', 'Zamin', 'Navro\'z', 'Sino', 'Atlas', 'Royal', 'Prime']
COMPANY_KIND = [('Biznes markazi', 'office', (900, 4500)), ('Savdo markazi', 'mall', (2500, 9000)),
                ('Mehmonxonasi', 'hotel', (1500, 5000)), ('Klinikasi', 'hospital', (600, 2500)),
                ('Xususiy maktabi', 'school', (1200, 3500)), ('Logistika ombori', 'warehouse', (2000, 8000)),
                ('IT Park ofisi', 'office', (400, 1500)), ('Turar-joy majmuasi', 'home', (1500, 6000)),
                ('Bog\'chasi', 'school', (500, 1400)), ('Restoran', 'other', (250, 900))]
ZONES = {
    'office': [('Qabulxona', 0.1, 'daily'), ('Ish xonalari', 0.55, 'daily'), ('Majlislar zali', 0.1, 'daily'),
               ('Oshxona', 0.08, 'disinfection'), ('Sanitariya tugunlari', 0.07, 'disinfection'),
               ('Yo\'laklar', 0.1, 'general')],
    'mall': [('Savdo qatorlari', 0.6, 'daily'), ('Food court', 0.15, 'disinfection'), ('Kirish va atrium', 0.1, 'daily'),
             ('Avtoturargoh', 0.1, 'general'), ('Sanitariya tugunlari', 0.05, 'disinfection')],
    'hotel': [('Xonalar', 0.6, 'daily'), ('Lobbi', 0.1, 'daily'), ('Restoran', 0.12, 'disinfection'),
              ('Spa va basseyn', 0.08, 'deep'), ('Yo\'laklar', 0.1, 'general')],
    'hospital': [('Palatalar', 0.45, 'disinfection'), ('Operatsiya bloki', 0.1, 'disinfection'),
                 ('Qabul bo\'limi', 0.15, 'daily'), ('Laboratoriya', 0.1, 'disinfection'), ('Yo\'laklar', 0.2, 'daily')],
    'school': [('Sinf xonalari', 0.55, 'daily'), ('Sport zali', 0.15, 'general'), ('Oshxona', 0.1, 'disinfection'),
               ('Yo\'laklar', 0.15, 'daily'), ('Sanitariya tugunlari', 0.05, 'disinfection')],
    'warehouse': [('Ombor zali', 0.75, 'general'), ('Ofis qismi', 0.1, 'daily'), ('Yuklash rampasi', 0.15, 'deep')],
    'home': [('Yashash xonalari', 0.6, 'daily'), ('Oshxona', 0.15, 'deep'), ('Hammom', 0.1, 'disinfection'),
             ('Dahliz', 0.15, 'daily')],
    'other': [('Zal', 0.6, 'daily'), ('Oshxona', 0.25, 'disinfection'), ('Sanitariya tugunlari', 0.15, 'disinfection')],
}
POSITIONS = ['Tozalovchi', 'Tozalovchi', 'Tozalovchi', 'Katta tozalovchi', 'Deraza yuvuvchi', 'Haydovchi',
             'Kimyoviy tozalash ustasi']
INTERACTION_SUBJECTS = [
    ('Narx bo\'yicha kelishuv', 'Xizmat hajmi va narxi kelishildi, tijoriy taklif yuborildi.'),
    ('Shartnomani uzaytirish', 'Mijoz shartnomani yana bir yilga uzaytirishga rozi bo\'ldi.'),
    ('Qo\'shimcha xizmat', 'Deraza yuvish xizmatini qo\'shishni so\'radi.'),
    ('Jadvalni o\'zgartirish', 'Tozalash vaqtini kechki 19:00 ga ko\'chirish so\'raldi.'),
    ('To\'lov eslatmasi', 'Muddati o\'tgan hisob-faktura bo\'yicha eslatma berildi.'),
    ('Sifat bo\'yicha fikr', 'Mijoz oxirgi tozalashdan mamnun ekanini aytdi.'),
    ('Obyektni ko\'rish', 'Menejer obyektga borib maydonni o\'lchadi.'),
]
REVIEW_COMMENTS = ["Juda sifatli, o'z vaqtida bajarildi!", "Brigada xushmuomala va tartibli.",
                   "Yaxshi, lekin biroz kechikishdi.", "Narxiga arziydi, tavsiya qilaman.",
                   "Hammasi chinni kabi toza, rahmat!", "Derazalar biroz dog' qoldi.", "Doimiy hamkorlik qilamiz.",
                   "Tez va sifatli ishlashdi.", "", ""]
COMPLAINTS = [
    ('Kechikish', 'Brigada belgilangan vaqtdan 30 daqiqa kech keldi.'),
    ('Deraza yuvilmagan', 'Ikkinchi qavat derazalari yuvilmay qolgan.'),
    ('Narx bo\'yicha savol', 'Hisob-fakturadagi summa kelishilgandan farq qiladi.'),
    ('Hid qoldi', 'Dezinfeksiyadan keyin kuchli hid saqlanib qoldi.'),
    ('Axlat olib chiqilmagan', 'Axlat qoplari obyektda qolib ketgan.'),
    ('Mebel shikastlangan', 'Polirovka paytida stol oyog\'i tirnalgan.'),
    ('Gilam to\'liq quritilmagan', 'Kimyoviy tozalashdan keyin gilam nam qoldi.'),
    ('Xodim xulqi', 'Xodim mijoz bilan qo\'pol gaplashdi.'),
]
LEAD_MESSAGES = ['Ofisimiz {a} m², haftada 3 marta tozalash kerak.', 'Ta\'mirdan keyin kvartira tozalash kerak ({a} m²).',
                 'Yangi bino uchun general tozalash narxini bilmoqchiman.', 'Gilam va divanlarni tozalash kerak.',
                 'Restoranimiz uchun kundalik dezinfeksiya xizmati kerak.', 'Narxlar ro\'yxatini yuboring.',
                 'Shanba kuni uyni to\'liq tozalab berasizlarmi?', '']
EXTRA_ITEMS = [('Gilam shampuni', 'chemical', 'litr', 10), ('Antiseptik gel', 'chemical', 'litr', 12),
               ('Yog\' ketkazuvchi vosita', 'chemical', 'litr', 8), ('Qog\'oz sochiq', 'consumable', 'rulon', 60),
               ('Suyuq sovun', 'consumable', 'litr', 25), ('Bir martalik niqob', 'consumable', 'dona', 100),
               ('Gubka', 'consumable', 'dona', 50), ('Bug\'li tozalagich', 'equipment', 'dona', 1),
               ('Yuvish aravachasi', 'equipment', 'dona', 3), ('Narvon (3 m)', 'equipment', 'dona', 2)]


class Command(BaseCommand):
    help = "Ko'p hajmli fake ma'lumotlar qo'shadi (mavjudlari saqlanadi)."

    def add_arguments(self, parser):
        parser.add_argument('--scale', type=float, default=1.0, help='Hajm koeffitsienti (standart 1)')
        parser.add_argument('--seed', type=int, default=2026, help='Tasodifiylik urug\'i')

    def n(self, base):
        return max(1, int(base * self.scale))

    def person(self, female=None):
        r = self.rnd
        if female is None:
            female = r.random() < 0.5
        first = r.choice(FEMALE if female else MALE)
        last = r.choice(SURNAMES) + ('a' if female else '')
        return first, last

    def phone(self):
        r = self.rnd
        return f'+998 {r.choice(["90", "91", "93", "94", "95", "97", "99", "33", "88"])} {r.randint(100, 999)} ' \
               f'{r.randint(10, 99)} {r.randint(10, 99)}'

    def address(self):
        r = self.rnd
        return f'Toshkent, {r.choice(DISTRICTS)} tumani, {r.choice(STREETS)} ko\'chasi, {r.randint(1, 120)}-uy'

    def username(self, base):
        name, i = base, 1
        while User.objects.filter(username=name).exists():
            i += 1
            name = f'{base}{i}'
        return name

    def contract_number(self, year):
        i = Contract.objects.count() + 1
        while Contract.objects.filter(number=f'SH-{year}-{i:04d}').exists():
            i += 1
        return f'SH-{year}-{i:04d}'

    @transaction.atomic
    def handle(self, *args, **opts):
        self.scale = opts['scale']
        self.rnd = rnd = random.Random(opts['seed'])
        today = timezone.localdate()
        D = datetime.timedelta
        counts = {}

        staff = {r: User.objects.filter(role=r).first() for r in ('manager', 'accountant', 'storekeeper', 'foreman')}

        # ---------------------------------------------------------- xizmatlar (bo'lmasa)
        services = list(ServiceType.objects.filter(is_active=True))
        if not services:
            self.stderr.write("Xizmat turlari yo'q. Avval: python manage.py seed_demo")
            return
        weights = [{'m2': 10, 'hour': 3, 'fixed': 1}[s.unit] for s in services]

        # ---------------------------------------------------------- brigadalar va xodimlar
        greek = ['Delta', 'Omega', 'Sigma', 'Lambda', 'Kappa', 'Zeta']
        teams = list(Team.objects.all())
        new_teams = []
        for name in greek[:self.n(3)]:
            if not Team.objects.filter(name=f'{name} brigada').exists():
                new_teams.append(Team.objects.create(name=f'{name} brigada', note='Qo\'shimcha brigada'))
        teams += new_teams
        new_emps = []
        for i in range(self.n(30)):
            first, last = self.person()
            pay = rnd.choice([('fixed', rnd.randint(28, 45) * 100_000), ('hourly', rnd.randint(15, 25) * 1000),
                              ('volume', rnd.randint(35, 60) * 10)])
            new_emps.append(Employee.objects.create(
                full_name=f'{first} {last}', position=rnd.choice(POSITIONS), phone=self.phone(),
                hire_date=today - D(days=rnd.randint(20, 1100)), pay_type=pay[0], pay_rate=pay[1],
                team=rnd.choice(teams),
                status=rnd.choices(['active', 'vacation', 'dismissed'], weights=[88, 7, 5])[0]))
        for t in new_teams:
            first, last = self.person(female=False)
            fm = Employee.objects.create(full_name=f'{first} {last}', position='Brigadir', phone=self.phone(), team=t,
                                         pay_type='fixed', pay_rate=rnd.randint(42, 55) * 100_000,
                                         hire_date=today - D(days=rnd.randint(400, 1500)))
            t.foreman = fm
            t.save()
            new_emps.append(fm)
        # bir nechta xodimga tizim hisobi
        for emp in new_emps[:self.n(6)]:
            role = 'foreman' if emp.position == 'Brigadir' else 'cleaner'
            first, _, last = emp.full_name.partition(' ')
            u = User.objects.create_user(username=self.username(f'xodim{emp.pk}'), password=PASSWORD,
                                         first_name=first, last_name=last, role=role, phone=emp.phone)
            emp.user = u
            emp.save()
        counts['Xodimlar'] = len(new_emps)
        all_emps = list(Employee.objects.exclude(status='dismissed'))

        # ---------------------------------------------------------- mijozlar, obyektlar, shartnomalar
        new_clients, new_facilities = [], []
        for i in range(self.n(40)):
            legal = rnd.random() < 0.6
            if legal:
                label, fkind, (amin, amax) = rnd.choice(COMPANY_KIND)
                name = f'{rnd.choice(COMPANY_WORDS)} {label}'
                if Client.objects.filter(name=name).exists():
                    name = f'{name} {rnd.randint(2, 99)}'
                cf, cl = self.person()
                c = Client.objects.create(
                    kind='legal', name=f'«{name}» MChJ' if rnd.random() < 0.5 else name,
                    stir=str(rnd.randint(200_000_000, 309_999_999)), contact_person=f'{cf} {cl}',
                    phone=self.phone(), email=f'info{rnd.randint(10, 9999)}@{rnd.choice(["mail.uz", "gmail.com", "company.uz"])}',
                    address=self.address(), note=rnd.choice(['', 'VIP mijoz', 'To\'lovni o\'z vaqtida qiladi',
                                                             'Kechki soatlarda ishlash talab qilinadi']))
                n_fac = rnd.choices([1, 2, 3], weights=[65, 25, 10])[0]
            else:
                first, last = self.person()
                fkind, (amin, amax) = rnd.choice([('home', (45, 220)), ('office', (30, 150))])
                c = Client.objects.create(kind='individual', name=f'{first} {last}', phone=self.phone(),
                                          email=f'{first.lower().replace(chr(39), "")}{rnd.randint(1, 999)}@gmail.com'
                                          if rnd.random() < 0.6 else '',
                                          address=self.address())
                n_fac = 1
            new_clients.append(c)
            for k in range(n_fac):
                area = Decimal(rnd.randint(amin, amax))
                f = Facility.objects.create(
                    client=c, name=c.name if n_fac == 1 else f'{c.name} — {k + 1}-filial', kind=fkind,
                    address=self.address(), area=area, floors=rnd.randint(1, 12 if legal else 2),
                    requirements=rnd.choice(['Har kuni ertalab 8:00 gacha tugatish.', 'Faqat ekologik vositalar.',
                                             'Kechki 19:00 dan keyin ishlash.', 'Hidsiz vositalardan foydalanish.', '']),
                    instructions=rnd.choice(['Kirishda qorovulga hujjat ko\'rsating.', 'Kalit administratorda.',
                                             'Avtoturargoh -1 qavatda.', '']),
                    status=rnd.choices(['active', 'inactive'], weights=[92, 8])[0])
                f.teams.add(rnd.choice(teams))
                f.employees.add(*rnd.sample(all_emps, min(len(all_emps), rnd.randint(1, 4))))
                for zn, share, ct in ZONES[fkind]:
                    Zone.objects.create(facility=f, name=zn, area=(area * Decimal(str(share))).quantize(Decimal('0.01')),
                                        cleaning_type=ct)
                freq = rnd.choice(['daily', 'weekly', 'monthly'])
                CleaningSchedule.objects.create(
                    facility=f, service=rnd.choices(services, weights=weights)[0], frequency=freq,
                    weekday=rnd.randint(0, 5) if freq == 'weekly' else None,
                    month_day=rnd.randint(1, 28) if freq == 'monthly' else None,
                    time=datetime.time(rnd.choice([6, 7, 8, 19, 20]), rnd.choice([0, 30])))
                new_facilities.append(f)
            if legal or rnd.random() < 0.3:
                start = today - D(days=rnd.randint(10, 700))
                end = start + D(days=rnd.choice([180, 365, 730]))
                status = 'expired' if end < today else rnd.choices(['active', 'draft', 'terminated'], weights=[85, 8, 7])[0]
                Contract.objects.create(client=c, number=self.contract_number(start.year), date=start, end_date=end,
                                        amount=rnd.randint(3, 250) * 1_000_000 if legal else rnd.randint(1, 10) * 500_000,
                                        status=status)
            for _ in range(rnd.randint(1, 4)):
                subj, text = rnd.choice(INTERACTION_SUBJECTS)
                Interaction.objects.create(client=c, date=today - D(days=rnd.randint(0, 300)),
                                           channel=rnd.choice(['phone', 'visit', 'email', 'telegram', 'other']),
                                           subject=subj, text=text, created_by=staff['manager'])
        # mijoz kabineti hisoblari
        for c in [c for c in new_clients if c.kind == 'individual'][:self.n(8)]:
            first, _, last = c.name.partition(' ')
            c.user = User.objects.create_user(username=self.username(f'mijoz{c.pk}'), password=PASSWORD,
                                              first_name=first, last_name=last, role='client', phone=c.phone)
            c.save()
        counts['Mijozlar'] = len(new_clients)
        counts['Obyektlar'] = len(new_facilities)

        # ---------------------------------------------------------- buyurtmalar (oxirgi 12 oy + kelgusi 2 hafta)
        facs = list(Facility.objects.filter(status='active').select_related('client'))
        new_orders = []
        for _ in range(self.n(400)):
            f = rnd.choice(facs)
            svc = rnd.choices(services, weights=weights)[0]
            offset = rnd.randint(-365, 14)
            d = today + D(days=offset)
            if offset < -2:
                status = rnd.choices(['done', 'cancelled'], weights=[92, 8])[0]
            elif offset <= 0:
                status = rnd.choice(['confirmed', 'in_progress', 'done'])
            else:
                status = rnd.choices(['new', 'confirmed'], weights=[45, 55])[0]
            if svc.unit == 'm2':
                qty = (f.area * Decimal(str(rnd.choice([1, 1, 1, 0.5, 0.3])))).quantize(Decimal('0.01'))
            else:
                qty = Decimal(rnd.randint(2, 10))
            contract = f.client.contracts.filter(status='active').first()
            new_orders.append(Order.objects.create(
                client=f.client, facility=f, service=svc, contract=contract,
                team=f.teams.first() or rnd.choice(teams), date=d,
                time=datetime.time(rnd.choice([7, 8, 9, 10, 14, 18, 19]), rnd.choice([0, 30])), status=status,
                quantity=qty, note=rnd.choice(['', '', 'Kalitni qorovuldan olish', 'Mijoz joyida bo\'ladi']),
                created_by=staff['manager']))
        counts['Buyurtmalar'] = len(new_orders)

        # ---------------------------------------------------------- hisob-fakturalar, to'lovlar, baholar
        n_inv = n_pay = n_rev = 0
        for o in new_orders:
            if o.status != 'done':
                continue
            inv = Invoice.objects.create(order=o, client=o.client, amount=o.total, date=o.date,
                                         due_date=o.date + D(days=rnd.choice([3, 7, 10, 15])),
                                         note=f'{o.service.name}, {o.facility.name}'[:255], created_by=staff['accountant'])
            n_inv += 1
            age = (today - o.date).days
            roll = rnd.random()
            # eski hisob-fakturalar ko'proq to'langan
            full_p = 0.9 if age > 60 else 0.6
            if roll < full_p:
                parts = rnd.choice([1, 1, 1, 2])
                paid = Decimal('0')
                for p in range(parts):
                    amount = o.total - paid if p == parts - 1 else (o.total / 2).quantize(Decimal('0.01'))
                    Payment.objects.create(invoice=inv, date=min(o.date + D(days=rnd.randint(0, 20)), today),
                                           amount=amount, method=rnd.choice(['cash', 'card', 'transfer']),
                                           created_by=staff['accountant'])
                    paid += amount
                    n_pay += 1
            elif roll < full_p + 0.12:
                Payment.objects.create(invoice=inv, date=min(o.date + D(days=rnd.randint(0, 15)), today),
                                       amount=(o.total * Decimal(str(rnd.choice([0.3, 0.5, 0.7])))).quantize(Decimal('0.01')),
                                       method='transfer', created_by=staff['accountant'])
                n_pay += 1
            if rnd.random() < 0.55:
                Review.objects.create(order=o, client=o.client, rating=rnd.choices([2, 3, 4, 5], weights=[1, 3, 8, 12])[0],
                                      comment=rnd.choice(REVIEW_COMMENTS), date=min(o.date + D(days=rnd.randint(0, 3)), today))
                n_rev += 1
        counts.update({'Hisob-fakturalar': n_inv, "To'lovlar": n_pay, 'Baholar': n_rev})

        # ---------------------------------------------------------- xarajatlar (har oy ijara + tasodifiy)
        n_exp = 0
        for m in range(12):
            d = (today.replace(day=1) - D(days=30 * m)).replace(day=5)
            Expense.objects.create(category='rent', amount=rnd.choice([4_000_000, 4_500_000]), date=d,
                                   note='Ofis ijarasi va kommunal', created_by=staff['accountant'])
            n_exp += 1
        notes = {'materials': ['Kimyoviy vositalar xaridi', 'Sarf materiallari', 'Uskuna ehtiyot qismlari'],
                 'transport': ['Yoqilg\'i', 'Taksi', 'Avtomobil ta\'miri'],
                 'other': ['Bank xizmati', 'Reklama', 'Ish kiyimlari', 'Aloqa xizmati']}
        for _ in range(self.n(150)):
            cat = rnd.choices(['materials', 'transport', 'other'], weights=[50, 30, 20])[0]
            amount = {'materials': rnd.randint(2, 30) * 100_000, 'transport': rnd.randint(1, 15) * 50_000,
                      'other': rnd.randint(1, 20) * 50_000}[cat]
            Expense.objects.create(category=cat, amount=amount, date=today - D(days=rnd.randint(0, 365)),
                                   facility=rnd.choice(facs) if cat != 'other' and rnd.random() < 0.7 else None,
                                   note=rnd.choice(notes[cat]), created_by=staff['accountant'])
            n_exp += 1

        # ---------------------------------------------------------- ombor
        suppliers = list(Supplier.objects.all())
        for name in ['Toza Dunyo Distribution', 'ProClean Asia', 'Hygiene Market']:
            if not Supplier.objects.filter(name=name).exists():
                suppliers.append(Supplier.objects.create(name=name, phone=self.phone(), address=self.address()))
        for name, kind, unit, minimum in EXTRA_ITEMS:
            if not InventoryItem.objects.filter(name=name).exists():
                InventoryItem.objects.create(name=name, kind=kind, unit=unit, min_quantity=minimum,
                                             price=rnd.randint(5, 900) * 1000)
        n_mov = 0
        items = list(InventoryItem.objects.filter(is_active=True))
        for it in items:
            StockMovement.objects.create(item=it, kind='in', quantity=Decimal(rnd.randint(2, 6)) * max(it.min_quantity, 1),
                                         date=today - D(days=rnd.randint(200, 360)), supplier=rnd.choice(suppliers),
                                         note='Yillik xarid', created_by=staff['storekeeper'])
            n_mov += 1
        for _ in range(self.n(200)):
            it = rnd.choice(items)
            it.refresh_from_db()
            kind = rnd.choices(['in', 'out', 'return'], weights=[25, 65, 10])[0]
            if kind == 'out':
                qty = min(Decimal(rnd.randint(1, 10)), it.quantity)
                if qty <= 0:
                    continue
            else:
                qty = Decimal(rnd.randint(1, 30 if kind == 'in' else 3))
            StockMovement.objects.create(
                item=it, kind=kind, quantity=qty, date=today - D(days=rnd.randint(0, 200)),
                facility=rnd.choice(facs) if kind == 'out' else None,
                employee=rnd.choice(all_emps) if kind in ('out', 'return') else None,
                supplier=rnd.choice(suppliers) if kind == 'in' else None, created_by=staff['storekeeper'])
            n_mov += 1
        counts['Ombor harakatlari'] = n_mov

        # ---------------------------------------------------------- davomat (yangi xodimlar, 45 kun) va smenalar
        n_att = 0
        for emp in [e for e in new_emps if e.status != 'dismissed']:
            for back in range(45):
                d = today - D(days=back)
                if d.weekday() == 6 or d < emp.hire_date:
                    continue
                if emp.status == 'vacation' and back < 10:
                    Attendance.objects.create(employee=emp, date=d, status='leave', note='Yillik ta\'til')
                elif (roll := rnd.random()) < 0.05:
                    Attendance.objects.create(employee=emp, date=d, status='absent', note='Sababsiz')
                elif roll < 0.08:
                    Attendance.objects.create(employee=emp, date=d, status='leave', note='Kasallik varaqasi')
                else:
                    cin = datetime.time(rnd.choice([7, 8, 8, 8, 9]), rnd.choice([0, 5, 15, 30, 45, 55]))
                    cout = datetime.time(rnd.randint(16, 19), rnd.choice([0, 15, 30, 45]))
                    Attendance.objects.create(employee=emp, date=d, facility=rnd.choice(facs), check_in=cin,
                                              check_out=cout if back > 0 else None)
                n_att += 1
            for fwd in range(7):
                if (today + D(days=fwd)).weekday() != 6:
                    Shift.objects.create(employee=emp, facility=rnd.choice(facs), date=today + D(days=fwd),
                                         start_time=datetime.time(rnd.choice([7, 8, 9]), 0),
                                         end_time=datetime.time(rnd.choice([16, 17, 18]), 0))
        counts['Davomat yozuvlari'] = n_att

        # ---------------------------------------------------------- ish haqi (oxirgi 3 oy; eskilari to'langan)
        n_pr = 0
        for back in (3, 2, 1):
            first = today.replace(day=1)
            for _ in range(back):
                first = (first - D(days=1)).replace(day=1)
            for emp in Employee.objects.exclude(status='dismissed'):
                rec, created = PayrollRecord.objects.get_or_create(
                    employee=emp, year=first.year, month=first.month,
                    defaults={'base': calc_base(emp, first.year, first.month),
                              'bonus': rnd.choice([0, 0, 0, 200_000, 500_000]),
                              'penalty': rnd.choice([0, 0, 0, 0, 100_000])})
                if created:
                    n_pr += 1
                    if back > 1 and rec.total > 0:
                        pay_day = (first + D(days=35)).replace(day=5)
                        rec.paid, rec.paid_date = True, pay_day
                        rec.save()
                        Expense.objects.create(category='salary', amount=rec.total, date=pay_day,
                                               note=f'Ish haqi: {emp} ({first.month:02d}.{first.year})',
                                               created_by=staff['accountant'])
        counts['Ish haqi yozuvlari'] = n_pr
        counts['Xarajatlar'] = n_exp

        # ---------------------------------------------------------- sifat nazorati
        criteria = ['Polni tozalash', 'Derazalar va oynalar', 'Hojatxona va sanitariya', 'Mebel va yuzalar',
                    "Axlat yig'ish", 'Hid va havo sifati']
        inspectors = list(Employee.objects.filter(position='Brigadir')) or all_emps
        for _ in range(self.n(50)):
            f = rnd.choice(facs)
            ins = Inspection.objects.create(
                facility=f, inspector=rnd.choice(inspectors), date=today - D(days=rnd.randint(0, 300)),
                order=f.orders.filter(status='done').order_by('?').first(),
                note=rnd.choice(['Reja bo\'yicha tekshiruv', 'Shikoyatdan keyingi tekshiruv', 'Kutilmagan tekshiruv']),
                created_by=staff['foreman'])
            zones = list(f.zones.all())
            for c in rnd.sample(criteria, rnd.randint(4, 6)):
                InspectionItem.objects.create(inspection=ins, criterion=c, zone=rnd.choice(zones) if zones else None,
                                              score=rnd.choices([2, 3, 4, 5], weights=[1, 3, 6, 10])[0],
                                              comment=rnd.choice(['', '', 'Yaxshi', 'Burchaklarda chang bor', 'Dog\'lar qolgan']))
            ins.recalc()
        assignees = list(User.objects.filter(role__in=['manager', 'foreman', 'admin']))
        for _ in range(self.n(25)):
            o = rnd.choice(new_orders)
            subj, content = rnd.choice(COMPLAINTS)
            status = rnd.choices(['new', 'in_progress', 'resolved', 'closed'], weights=[20, 20, 35, 25])[0]
            Complaint.objects.create(client=o.client, order=o, subject=subj, content=content,
                                     date=min(o.date + D(days=1), today), status=status,
                                     assignee=rnd.choice(assignees) if status != 'new' else None,
                                     resolution='Brigada ogohlantirildi, bepul qayta tozalandi.'
                                     if status in ('resolved', 'closed') else '')
        for _ in range(self.n(30)):
            first, last = self.person()
            Lead.objects.create(name=f'{first} {last}', phone=self.phone(), service=rnd.choice(services + [None]),
                                address=self.address() if rnd.random() < 0.6 else '',
                                message=rnd.choice(LEAD_MESSAGES).format(a=rnd.randint(40, 500)),
                                status=rnd.choices(['new', 'contacted', 'converted', 'rejected'], weights=[35, 30, 20, 15])[0])
        counts.update({'Tekshiruvlar': self.n(50), 'Shikoyatlar': self.n(25), 'Arizalar': self.n(30)})

        self.stdout.write(self.style.SUCCESS("Fake ma'lumotlar qo'shildi:"))
        for k, v in counts.items():
            self.stdout.write(f'  {k:22} +{v}')
        self.stdout.write(f"Yangi xodim/mijoz hisoblari paroli: {PASSWORD} (loginlar: xodim<ID>, mijoz<ID>)")
