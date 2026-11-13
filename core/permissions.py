"""Rollar va ruxsatlar matritsasi (TZ 4-bo'lim).

PERMS[bo'lim] = (ko'rish mumkin bo'lgan rollar, o'zgartirish mumkin bo'lgan rollar)
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

A, D, M, F, C, B, S, K = 'admin', 'director', 'manager', 'foreman', 'cleaner', 'accountant', 'storekeeper', 'client'

PERMS = {
    'dashboard': ((A, D, M), ()),
    'clients': ((A, D, M), (A, M)),
    'contracts': ((A, D, M), (A, M)),
    'leads': ((A, D, M), (A, M)),
    'facilities': ((A, D, M, F), (A, M)),
    'services': ((A, D, M, B), (A, M)),
    'orders': ((A, D, M, F), (A, M)),
    'employees': ((A, D, M, F, B), (A, M)),
    'teams': ((A, D, M, F), (A, M)),
    'shifts': ((A, D, M, F), (A, M, F)),
    'attendance': ((A, D, M, F, B), (A, M, F)),
    'payroll': ((A, D, B), (A, B)),
    'my_tasks': ((C, F), (C, F)),
    'inventory': ((A, D, M, S), (A, S)),
    'movements': ((A, D, M, S), (A, S)),
    'suppliers': ((A, D, M, S), (A, S)),
    'invoices': ((A, D, M, B), (A, B)),
    'payments': ((A, D, B), (A, B)),
    'expenses': ((A, D, B), (A, B)),
    'inspections': ((A, D, M, F), (A, M, F)),
    'complaints': ((A, D, M, F), (A, M, F)),
    'reviews': ((A, D, M, F), (A, M)),
    'ratings': ((A, D, M, F), ()),
    'reports': ((A, D, B), ()),
    'users': ((A,), (A,)),
    'audit': ((A, D), ()),
}

# (guruh, [(bo'lim, nom, ikonka, url_name), ...])
MENU = [
    ('Asosiy', [
        ('dashboard', 'Dashboard', 'bi-speedometer2', 'dashboard'),
        ('my_tasks', 'Mening vazifalarim', 'bi-list-check', 'my_tasks'),
    ]),
    ('Mijozlar va obyektlar', [
        ('clients', 'Mijozlar', 'bi-people', 'clients_list'),
        ('contracts', 'Shartnomalar', 'bi-file-earmark-text', 'contracts_list'),
        ('leads', 'Arizalar', 'bi-inbox', 'leads_list'),
        ('facilities', 'Obyektlar', 'bi-buildings', 'facilities_list'),
        ('services', 'Xizmatlar va narxlar', 'bi-stars', 'services_list'),
        ('orders', 'Buyurtmalar', 'bi-clipboard-check', 'orders_list'),
    ]),
    ('Xodimlar', [
        ('employees', 'Xodimlar', 'bi-person-badge', 'employees_list'),
        ('teams', 'Brigadalar', 'bi-people-fill', 'teams_list'),
        ('shifts', 'Ish jadvali', 'bi-calendar-week', 'shifts_list'),
        ('attendance', 'Davomat', 'bi-clock-history', 'attendance_list'),
        ('payroll', 'Ish haqi', 'bi-cash-coin', 'payroll'),
    ]),
    ('Ombor', [
        ('inventory', 'Mahsulotlar', 'bi-box-seam', 'inventory_list'),
        ('movements', 'Kirim-chiqim', 'bi-arrow-left-right', 'movements_list'),
        ('suppliers', 'Yetkazib beruvchilar', 'bi-truck', 'suppliers_list'),
    ]),
    ('Moliya', [
        ('invoices', 'Hisob-fakturalar', 'bi-receipt', 'invoices_list'),
        ('payments', "To'lovlar", 'bi-credit-card', 'payments_list'),
        ('expenses', 'Xarajatlar', 'bi-wallet2', 'expenses_list'),
    ]),
    ('Sifat nazorati', [
        ('inspections', 'Tekshiruvlar', 'bi-clipboard2-check', 'inspections_list'),
        ('complaints', 'Shikoyatlar', 'bi-exclamation-triangle', 'complaints_list'),
        ('reviews', 'Baholar', 'bi-star', 'reviews_list'),
        ('ratings', 'Sifat reytingi', 'bi-trophy', 'ratings'),
    ]),
    ('Tizim', [
        ('reports', 'Hisobotlar', 'bi-bar-chart-line', 'reports'),
        ('users', 'Foydalanuvchilar', 'bi-shield-lock', 'users_list'),
        ('audit', 'Amallar jurnali', 'bi-journal-text', 'audit_list'),
    ]),
]


def can(user, section, mode='view'):
    """Foydalanuvchi shu bo'limda amal bajara oladimi? mode: 'view' yoki 'edit'."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    entry = PERMS.get(section)
    if not entry:
        return False
    roles = entry[0] if mode == 'view' else entry[1]
    return user.role in roles


def section_required(section, mode='view'):
    """Funksiya-view uchun dekorator: kirmagan bo'lsa login sahifasiga, ruxsati yo'q bo'lsa 403."""

    def deco(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not can(request.user, section, mode):
                raise PermissionDenied
            return fn(request, *args, **kwargs)

        return wrapper

    return deco


def role_required(*roles):
    """Muayyan rollar uchun dekorator (mijoz kabineti kabi bo'limlarda)."""

    def deco(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not (request.user.is_superuser or request.user.role in roles):
                raise PermissionDenied
            return fn(request, *args, **kwargs)

        return wrapper

    return deco
