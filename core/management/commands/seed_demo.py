"""Demo ma'lumotlar: tizimni sinash va taqdimot uchun.

    python manage.py seed_demo           # bo'sh bazaga
    python manage.py seed_demo --force   # mavjud ma'lumotlar ustiga qo'shadi

Barcha demo foydalanuvchilar paroli: demo12345
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
from hr.models import Attendance, Employee, Shift, Team
from inventory.models import InventoryItem, StockMovement, Supplier
from orders.models import Order, ServiceType
from quality.models import Complaint, Inspection, InspectionItem, Review

PASSWORD = 'demo12345'
DISTRICTS = ["Chilonzor", "Yunusobod", "Mirzo Ulug'bek", "Shayxontohur", "Yakkasaroy"]


class Command(BaseCommand):
    help = "Demo ma'lumotlar yaratadi (test va taqdimot uchun)."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help="Mavjud ma'lumotlar bo'lsa ham qo'shish")

    @transaction.atomic
    def handle(self, *args, **opts):
        if Client.objects.exists() and not opts['force']:
            self.stdout.write(self.style.WARNING("Bazada allaqachon ma'lumot bor. --force bilan qayta ishga tushiring."))
            return
        rnd = random.Random(42)
        today = timezone.localdate()
        D = datetime.timedelta

        # ---------------------------------------------------------- foydalanuvchilar
        spec = [
            ('admin', 'admin', 'Kamron', 'Ibaydullayev'), ('direktor', 'director', 'Sardor', 'Alimov'),
            ('menejer', 'manager', 'Madina', 'Rustamova'), ('brigadir', 'foreman', 'Otabek', 'Qodirov'),
            ('tozalovchi', 'cleaner', 'Gulnora', 'Saidova'), ('buxgalter', 'accountant', 'Nodira', 'Ergasheva'),
            ('omborchi', 'storekeeper', 'Akmal', 'Hasanov'), ('mijoz', 'client', 'Dilnoza', 'Yusupova'),
        ]
        users = {}
        for username, role, first, last in spec:
            u, created = User.objects.get_or_create(
                username=username, defaults={'first_name': first, 'last_name': last, 'role': role,
                                             'phone': '+998 90 123 45 6' + str(len(users))})
            if created:
                u.set_password(PASSWORD)
                u.save()
            users[username] = u

        # ---------------------------------------------------------- xizmatlar
        svc_spec = [
            ('Kundalik tozalash', 'Ofis va binolarni har kuni tozalash: polni yuvish, changni artish, axlatni chiqarish.', 'm2', 3000, 'bi-brush'),
            ('General tozalash', 'Butun obyektni chuqur tozalash: mebel, devor, sanitariya tugunlari.', 'm2', 9000, 'bi-stars'),
            ('Deraza va fasad yuvish', "Ichki va tashqi oynalarni profesional yuvish.", 'm2', 6000, 'bi-window'),
            ("Ta'mirdan keyingi tozalash", "Qurilish changi, bo'yoq va yelim izlarini ketkazish.", 'm2', 12000, 'bi-hammer'),
            ('Kimyoviy tozalash', 'Gilam, divan va yumshoq mebelni kimyoviy tozalash.', 'm2', 15000, 'bi-droplet'),
            ('Dezinfeksiya', 'Maxsus vositalar bilan sanitar ishlov berish.', 'm2', 4000, 'bi-shield-check'),
            ('Soatbay yordamchi', 'Bir martalik ishlar uchun soatbay tozalovchi.', 'hour', 60000, 'bi-clock'),
            ('Maxsus buyurtma (belgilangan narx)', 'Standart bo\'lmagan ishlar uchun kelishilgan narx.', 'fixed', 500000, 'bi-gem'),
        ]
        services = [ServiceType.objects.create(name=n, description=d, unit=u, price=p, icon=i)
                    for n, d, u, p, i in svc_spec]
        daily, general = services[0], services[1]

        # ---------------------------------------------------------- xodimlar va brigadalar
        team_names = ['Alfa brigada', 'Beta brigada', 'Gamma brigada']
        teams = [Team.objects.create(name=n, note='Asosiy tozalash brigadasi') for n in team_names]
        first_names = ['Gulnora Saidova', 'Sevara Normatova', 'Malika Ismoilova', 'Dilshod Karimov', 'Rustam Aliyev',
                       'Zarina Qosimova', 'Nigora Toshpulatova', 'Bekzod Mirzayev', 'Shahlo Abdullayeva',
                       'Ulugbek Turgunov', 'Feruza Nazarova', 'Jahongir Sobirov']
        employees = []
        for i, name in enumerate(first_names):
            team = teams[i % 3]
            pay = [('fixed', 3_000_000), ('hourly', 18_000), ('volume', 450)][i % 3]
            employees.append(Employee.objects.create(
                full_name=name, position='Tozalovchi', phone=f'+998 91 555 00 {i:02d}', team=team,
                hire_date=today - D(days=rnd.randint(60, 600)), pay_type=pay[0], pay_rate=pay[1]))
        foremen = [Employee.objects.create(full_name=n, position='Brigadir', phone=f'+998 93 777 00 {i:02d}',
                                           team=teams[i], pay_type='fixed', pay_rate=4_500_000,
                                           hire_date=today - D(days=900))
                   for i, n in enumerate(['Otabek Qodirov', 'Sherzod Rahmonov', 'Laziz Ortiqov'])]
        for t, f in zip(teams, foremen):
            t.foreman = f
            t.save()
        foremen[0].user = users['brigadir']
        foremen[0].save()
        employees[0].user = users['tozalovchi']
        employees[0].save()
        everyone = employees + foremen

        # ---------------------------------------------------------- mijozlar va obyektlar
        client_spec = [
            ('legal', 'Tashkent City Mall MChJ', '305123456', 'mall', 4800), ('legal', 'Orient Hotel', '305223344', 'hotel', 2600),
            ('legal', "45-sonli maktab", '201998877', 'school', 3200), ('legal', "Sog'lom klinikasi", '305667788', 'hospital', 1450),
            ('legal', 'Digital Park Ofis', '307445566', 'office', 1800), ('legal', "Bahor turar-joy majmuasi", '306112233', 'home', 2200),
            ('individual', 'Dilnoza Yusupova', '', 'home', 96), ('individual', 'Jasur Toshmatov', '', 'home', 120),
            ('individual', 'Aziza Karimova', '', 'office', 64), ('individual', 'Bobur Rahimov', '', 'home', 85),
        ]
        clients, facilities = [], []
        for i, (kind, name, stir, fkind, area) in enumerate(client_spec):
            c = Client.objects.create(kind=kind, name=name, stir=stir, phone=f'+998 90 {100 + i} 22 3{i}',
                                      email=f'client{i}@example.uz', address='Toshkent shahri',
                                      contact_person='' if kind == 'individual' else 'Mas\'ul shaxs')
            clients.append(c)
            n_fac = 2 if kind == 'legal' and i % 2 == 0 else 1
            for k in range(n_fac):
                f = Facility.objects.create(
                    client=c, name=name if n_fac == 1 else f'{name} — {k + 1}-bino', kind=fkind,
                    address='Toshkent, %s tumani, %d-uy' % (rnd.choice(DISTRICTS), rnd.randint(1, 60)),
                    area=Decimal(area) / n_fac, floors=rnd.randint(1, 5),
                    requirements='Har kuni ertalab 8:00 gacha tugatish. Toza havo va hidsizlik.',
                    instructions="Kirish uchun qorovuldan ruxsatnoma oling.")
                f.teams.add(teams[len(facilities) % 3])
                f.employees.add(*rnd.sample(employees, 2))
                facilities.append(f)
                for zn, share, ct in [('Kirish zonasi', 0.15, 'daily'), ('Asosiy xonalar', 0.6, 'daily'),
                                      ('Sanitariya tugunlari', 0.1, 'disinfection'), ('Zinapoya va yo\'laklar', 0.15, 'general')]:
                    Zone.objects.create(facility=f, name=zn, area=round(f.area * Decimal(str(share)), 2), cleaning_type=ct)
                CleaningSchedule.objects.create(facility=f, service=daily, frequency='daily', time=datetime.time(7, 0))
                if f.area > 1000:
                    CleaningSchedule.objects.create(facility=f, service=general, frequency='monthly', month_day=25,
                                                    time=datetime.time(19, 0))
            Contract.objects.create(client=c, number=f'SH-{2026}-{i + 1:03d}', date=today - D(days=rnd.randint(30, 300)),
                                    end_date=today + D(days=rnd.randint(-20, 300)), amount=rnd.randint(10, 120) * 1_000_000,
                                    status='active')
            Interaction.objects.create(client=c, date=today - D(days=rnd.randint(1, 60)), channel=rnd.choice(['phone', 'visit', 'telegram']),
                                       subject='Narx bo\'yicha kelishuv', text='Mijoz bilan xizmat hajmi va narx kelishildi.',
                                       created_by=users['menejer'])
        clients[6].user = users['mijoz']
        clients[6].save()

        # ---------------------------------------------------------- buyurtmalar, hisob-fakturalar, to'lovlar
        orders = []
        for _ in range(80):
            c = rnd.choice(clients)
            f = rnd.choice(list(c.facilities.all()))
            svc = rnd.choices(services, weights=[40, 14, 10, 6, 6, 8, 6, 2])[0]
            offset = rnd.randint(-130, 8)
            d = today + D(days=offset)
            if offset < -1:
                status = rnd.choices(['done', 'cancelled'], weights=[90, 10])[0]
            elif offset <= 0:
                status = rnd.choice(['in_progress', 'done', 'confirmed'])
            else:
                status = rnd.choice(['new', 'confirmed'])
            qty = f.area if svc.unit == 'm2' else Decimal(rnd.randint(2, 8))
            team = f.teams.first()
            orders.append(Order.objects.create(
                client=c, facility=f, service=svc, team=team, date=d, time=datetime.time(rnd.choice([7, 8, 9, 14, 18]), 0),
                status=status, quantity=qty, created_by=users['menejer']))
        # takrorlanuvchi buyurtma namunasi
        rec = Order.objects.create(client=clients[4], facility=clients[4].facilities.first(), service=daily,
                                   team=teams[0], date=today, status='confirmed', quantity=clients[4].facilities.first().area,
                                   recurrence='weekly', recurrence_end=today + D(days=28), created_by=users['menejer'])
        rec.generate_recurrences()

        comments = ["Juda sifatli va o'z vaqtida bajarildi, rahmat!", "Brigada xushmuomala, hammasi toza.",
                    "Yaxshi ish, lekin biroz kechikishdi.", "Doimiy hamkorlik qilamiz.", "Narxiga arziydi."]
        for o in Order.objects.filter(status='done'):
            inv = Invoice.objects.create(order=o, client=o.client, amount=o.total, date=o.date,
                                         due_date=o.date + D(days=7), note=o.service.name, created_by=users['buxgalter'])
            roll = rnd.random()
            pay_date = min(o.date + D(days=rnd.randint(0, 9)), today)
            if roll < 0.68:
                Payment.objects.create(invoice=inv, date=pay_date, amount=o.total,
                                       method=rnd.choice(['cash', 'card', 'transfer']), created_by=users['buxgalter'])
            elif roll < 0.83:
                Payment.objects.create(invoice=inv, date=pay_date, amount=(o.total / 2).quantize(Decimal('0.01')),
                                       method='transfer', created_by=users['buxgalter'])
            if rnd.random() < 0.6:
                Review.objects.create(order=o, client=o.client, rating=rnd.choices([3, 4, 5], weights=[1, 4, 6])[0],
                                      comment=rnd.choice(comments), date=min(o.date + D(days=1), today))

        # ---------------------------------------------------------- xarajatlar
        for _ in range(40):
            cat = rnd.choice(['salary', 'materials', 'transport', 'rent', 'other'])
            amount = {'salary': rnd.randint(8, 25) * 500_000, 'materials': rnd.randint(2, 12) * 250_000,
                      'transport': rnd.randint(1, 6) * 100_000, 'rent': rnd.randint(3, 8) * 500_000,
                      'other': rnd.randint(1, 5) * 100_000}[cat]
            Expense.objects.create(category=cat, amount=amount, date=today - D(days=rnd.randint(0, 130)),
                                   facility=rnd.choice(facilities) if cat in ('materials', 'transport') else None,
                                   note={'salary': 'Ish haqi', 'materials': 'Kimyoviy vositalar xaridi', 'transport': 'Yo\'l kira',
                                         'rent': 'Ofis ijarasi', 'other': 'Boshqa xarajat'}[cat], created_by=users['buxgalter'])

        # ---------------------------------------------------------- ombor
        suppliers = [Supplier.objects.create(name=n, phone=f'+998 71 200 00 0{i}') for i, n in
                     enumerate(["Kimyo Savdo MChJ", "CleanTech Supply", "Uskuna-Servis"])]
        item_spec = [
            ('Pol yuvish vositasi', 'chemical', 'litr', 20, 300), ('Oyna tozalagich', 'chemical', 'litr', 10, 60),
            ('Dezinfeksiya eritmasi', 'chemical', 'litr', 15, 25), ('Axlat paketlari', 'consumable', 'paket', 30, 200),
            ('Qo\'lqop (juft)', 'consumable', 'juft', 50, 40), ('Latta (mikrofibra)', 'consumable', 'dona', 40, 25),
            ('Chang yutgich', 'equipment', 'dona', 2, 6), ('Polirovka mashinasi', 'equipment', 'dona', 1, 3),
            ('Shvabra to\'plami', 'equipment', 'dona', 5, 12), ('Hojatxona qog\'ozi', 'consumable', 'dona', 100, 150),
        ]
        for name, kind, unit, minimum, start in item_spec:
            it = InventoryItem.objects.create(name=name, kind=kind, unit=unit, min_quantity=minimum,
                                              price=rnd.randint(5, 200) * 1000)
            StockMovement.objects.create(item=it, kind='in', quantity=start, date=today - D(days=120),
                                         supplier=rnd.choice(suppliers), note='Boshlang\'ich kirim', created_by=users['omborchi'])
            for _ in range(rnd.randint(2, 5)):
                it.refresh_from_db()
                qty = min(Decimal(rnd.randint(1, 8)), it.quantity)
                if qty > 0:
                    StockMovement.objects.create(item=it, kind='out', quantity=qty, date=today - D(days=rnd.randint(0, 100)),
                                                 facility=rnd.choice(facilities), employee=rnd.choice(everyone),
                                                 created_by=users['omborchi'])
        # ikkitasini kam qoldiqqa tushiramiz (ogohlantirishni ko'rsatish uchun)
        for name in ('Dezinfeksiya eritmasi', 'Oyna tozalagich'):
            it = InventoryItem.objects.get(name=name)
            extra = it.quantity - it.min_quantity + 2
            if extra > 0:
                StockMovement.objects.create(item=it, kind='out', quantity=extra, date=today - D(days=1),
                                             facility=facilities[0], created_by=users['omborchi'])

        # ---------------------------------------------------------- davomat va smenalar
        for emp in everyone:
            for back in range(25):
                d = today - D(days=back)
                if d.weekday() == 6:
                    continue
                roll = rnd.random()
                if roll < 0.06:
                    Attendance.objects.create(employee=emp, date=d, status='absent', note='Sababsiz')
                elif roll < 0.09:
                    Attendance.objects.create(employee=emp, date=d, status='leave', note='Ruxsat')
                else:
                    cin = datetime.time(rnd.randint(8, 9), rnd.choice([0, 10, 20, 35, 50]))
                    cout = datetime.time(rnd.randint(17, 18), rnd.choice([0, 15, 30, 45]))
                    Attendance.objects.create(employee=emp, date=d, facility=rnd.choice(facilities),
                                              check_in=cin, check_out=cout if back > 0 else None)
            for fwd in range(0, 7):
                Shift.objects.create(employee=emp, facility=rnd.choice(facilities), date=today + D(days=fwd),
                                     start_time=datetime.time(9, 0), end_time=datetime.time(18, 0))

        # ---------------------------------------------------------- sifat nazorati
        criteria = ['Polni tozalash', 'Derazalar va oynalar', 'Hojatxona va sanitariya', 'Mebel va yuzalar', "Axlat yig'ish"]
        for _ in range(16):
            f = rnd.choice(facilities)
            ins = Inspection.objects.create(facility=f, inspector=rnd.choice(foremen), date=today - D(days=rnd.randint(0, 90)),
                                            note='Reja bo\'yicha tekshiruv', created_by=users['brigadir'])
            for c in criteria:
                InspectionItem.objects.create(inspection=ins, criterion=c, score=rnd.choices([3, 4, 5], weights=[1, 3, 6])[0])
            ins.recalc()
        for i, (subject, content) in enumerate([
            ('Kechikish', 'Brigada belgilangan vaqtdan 40 daqiqa kech keldi.'),
            ('Deraza yuvilmagan', 'Ikkinchi qavat derazalari yuvilmay qolgan.'),
            ('Narx bo\'yicha savol', 'Hisob-fakturadagi summa kelishilgandan farq qiladi.'),
            ('Hid', 'Dezinfeksiyadan keyin kuchli hid saqlanib qoldi.'),
            ('Axlat', 'Axlat qoplari olib chiqilmagan.')]):
            Complaint.objects.create(client=rnd.choice(clients), subject=subject, content=content,
                                     date=today - D(days=rnd.randint(0, 30)),
                                     status=['new', 'in_progress', 'resolved', 'closed', 'new'][i],
                                     assignee=users['menejer'] if i else None,
                                     resolution='Brigada ogohlantirildi, qayta tozalandi.' if i in (2, 3) else '')
        for name, phone, msg in [("Hamid Orifov", "+998 90 111 22 33", "Ofisimiz 150 m², haftada 3 marta tozalash kerak."),
                                 ("Lola Ahmedova", "+998 93 444 55 66", "Ta'mirdan keyin kvartira tozalash kerak."),
                                 ("Qurilish MChJ", "+998 71 200 30 40", "Yangi bino uchun general tozalash.")]:
            Lead.objects.create(name=name, phone=phone, message=msg, service=rnd.choice(services))

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar yaratildi."))
        self.stdout.write(f"Kirish uchun login / parol (parol hammasida: {PASSWORD}):")
        for username, role, *_ in spec:
            self.stdout.write(f"  {username:12} — {User.Role(role).label}")
