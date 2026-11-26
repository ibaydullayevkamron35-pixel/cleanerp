# CleanERP — Tozalash kompaniyalari va obyektlarni boshqarish ERP

Muallif: Ibaydullayev Kamron · Texnologiya: Python, Django, HTML/CSS/JS (Bootstrap, Chart.js)

Texnik topshiriq (TZ v1.0) asosida yozilgan veb-ilova.

## Ishga tushirish

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations accounts core crm facilities orders hr inventory finance quality
python manage.py migrate
python manage.py seed_demo        # demo ma'lumotlar (ixtiyoriy, lekin tavsiya etiladi)
python manage.py runserver
```

Brauzerda: <http://127.0.0.1:8000/> (ochiq sayt), <http://127.0.0.1:8000/kirish/> (tizimga kirish).

> Sahifalar Bootstrap, Bootstrap Icons, Chart.js va Google Fonts'ni CDN'dan yuklaydi — ishlash uchun internet kerak.

### Demo foydalanuvchilar (`seed_demo` dan keyin, parol hammasida `demo12345`)

| Login | Rol | Kirgach ochiladi |
|---|---|---|
| `admin` | Administrator | Dashboard, hamma bo'limlar, `/admin/` |
| `direktor` | Rahbar | Dashboard, hisobotlar (ko'rish) |
| `menejer` | Menejer | Mijozlar, obyektlar, buyurtmalar, xodimlar |
| `brigadir` | Brigadir | Mening vazifalarim, davomat, tekshiruvlar |
| `tozalovchi` | Tozalovchi xodim | Mening vazifalarim (kelish/ketish, bajarildi) |
| `buxgalter` | Buxgalter | Hisob-fakturalar, to'lovlar, xarajatlar, ish haqi |
| `omborchi` | Omborchi | Ombor, kirim-chiqim, inventarizatsiya |
| `mijoz` | Mijoz | Shaxsiy kabinet (`/kabinet/`) |

Haqiqiy administrator yaratish: `python manage.py createsuperuser` (avtomatik "Administrator" roli oladi).

## Loyiha tuzilishi

| Ilova | TZ moduli | Asosiy modellar |
|---|---|---|
| `accounts` | 5.1 Autentifikatsiya, rollar | `User` (8 rol), kirish, ro'yxatdan o'tish, profil |
| `core` | 5.1 Amallar jurnali, umumiy CRUD | `AuditLog`, `Crud` generatori, ruxsatlar matritsasi |
| `crm` | 5.2 Mijozlar | `Client`, `Contract`, `Interaction`, `Lead` |
| `facilities` | 5.3 Obyektlar | `Facility`, `Zone`, `CleaningSchedule` |
| `orders` | 5.4 Xizmatlar va buyurtmalar | `ServiceType`, `Order` (takroriy buyurtmalar bilan) |
| `hr` | 5.5 Xodimlar va jadval | `Employee`, `Team`, `Shift`, `Attendance`, `PayrollRecord` |
| `inventory` | 5.6 Ombor | `InventoryItem`, `StockMovement`, `Supplier` |
| `finance` | 5.7 Moliya | `Invoice` (PDF), `Payment`, `Expense` |
| `quality` | 5.8 Sifat nazorati | `Inspection`, `InspectionItem`, `Complaint`, `Review` |
| `reports` | 5.9 Dashboard va hisobotlar | Chart.js grafiklar, 7 ta hisobot, Excel/PDF |
| `website` | 5.10 Ochiq sayt va kabinet | Landing, narxlar, ariza formasi, mijoz kabineti |

## Muhim qoidalar (biznes-mantiq)

- **Buyurtma summasi** avtomatik: `m²` yoki soatbay xizmatda `miqdor × narx`, belgilangan narxda — narxning o'zi. Birlik narxi bo'sh qolsa, xizmat narxi olinadi.
- **Takroriy buyurtmalar**: buyurtmada "Har kuni/hafta/oy" tanlansa, buyurtma sahifasidagi tugma bilan kelgusi 60 kun uchun nusxalar yaratiladi (qayta bosish takrorlamaydi).
- **Hisob-faktura holati** to'lovlarga qarab avtomatik o'zgaradi (to'lanmagan → qisman → to'langan). Qarzdan ortiq to'lov qabul qilinmaydi.
- **Ombor qoldig'i** faqat kirim/chiqim harakatlari orqali o'zgaradi. Qoldiqdan ortiq chiqim mumkin emas. Minimal qoldiqdan tushsa — dashboard va ro'yxatda ogohlantirish.
- **Ish haqi**: belgilangan oylik / davomat soatlari × stavka / brigadaning bajargan m² hajmi (a'zolar o'rtasida teng) × stavka. "To'landi" bosilganda xarajatlarga avtomatik yoziladi.
- **Bog'liq yozuvlarni o'chirish** tizim tomonidan taqiqlanadi (masalan, buyurtmasi bor mijozni o'chirib bo'lmaydi) va tushunarli xabar chiqadi.
- Barcha muhim amallar **Amallar jurnali**ga yoziladi (kim, nima, qachon).

## Ruxsatlar

Rollar va ruxsatlar `core/permissions.py` dagi `PERMS` jadvalida. Yangi rol yoki bo'lim qo'shish uchun shu fayl va `User.Role` ni o'zgartirish yetarli. Mijoz faqat o'z ma'lumotlarini ko'radi (kabinet view'lari `client_profile` bo'yicha filtrlaydi).

## Yangi bo'lim qo'shish

`core/crud.py` dagi `Crud(...)` bilan ro'yxat, qo'shish, tahrirlash, o'chirish, qidiruv, filtr, sahifalash va Excel eksport bitta e'lon bilan tayyor bo'ladi. Namuna: `crm/urls.py`.

## Testlar

```bash
python manage.py test
```

Testlar biznes-mantiq (summa, hisob-faktura, ombor), rollar bo'yicha ruxsatlar, barcha ro'yxat/detail sahifalarining ochilishi va hisobot eksportini tekshiradi.

## Ishga tushirish (production) uchun

- `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<uzun tasodifiy qiymat>`, `DJANGO_ALLOWED_HOSTS=sayt.uz`
- PostgreSQL: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` muhit o'zgaruvchilarini bering va `psycopg[binary]` o'rnating.
- `python manage.py collectstatic`, gunicorn/nginx orqali xizmat ko'rsating.
- Ma'lumotlar bazasining muntazam zaxira nusxasini oling (`pg_dump` yoki `python manage.py dumpdata`).
- Demo parollarni (`demo12345`) o'zgartiring yoki demo foydalanuvchilarni o'chiring.
