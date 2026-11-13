from django.contrib import messages
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import AuditLog
from core.permissions import role_required
from crm.models import Client
from facilities.models import Facility
from orders.models import Order, ServiceType
from quality.models import Review

from .forms import CabinetFacilityForm, CabinetOrderForm, ComplaintForm, LeadForm, ReviewForm


# ------------------------------------------------------------------ ochiq sayt
def landing(request):
    # Xodim (mijoz bo'lmagan) tizimga kirgan bo'lsa, sayt manzili uni to'g'ridan-to'g'ri panelga olib o'tadi.
    # Ochiq saytni ko'rish uchun: /?sayt=1
    u = request.user
    if (request.method == 'GET' and u.is_authenticated and u.role != 'client'
            and not request.GET.get('sayt')):
        return redirect('home')
    form = LeadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Arizangiz qabul qilindi! Menejerimiz tez orada siz bilan bog'lanadi.")
        return redirect(reverse('landing') + '#ariza')
    services = ServiceType.objects.filter(is_active=True)
    reviews = Review.objects.filter(rating__gte=4).exclude(comment='').select_related('client', 'order')[:3]
    stats = {
        'clients': Client.objects.count(),
        'facilities': Facility.objects.filter(status='active').count(),
        'done': Order.objects.filter(status='done').count(),
        'rating': Review.objects.aggregate(a=Avg('rating'))['a'],
    }
    return render(request, 'website/home.html', {
        'form': form, 'services': services, 'reviews': reviews, 'stats': stats,
    })


def services_page(request):
    return render(request, 'website/services.html', {'services': ServiceType.objects.filter(is_active=True)})


# ------------------------------------------------------------------ mijoz kabineti
def _client(request):
    client = getattr(request.user, 'client_profile', None)
    if client is None:
        client = Client.objects.create(user=request.user, name=request.user.display_name,
                                       phone=request.user.phone or '—')
    return client


@role_required('client')
def cabinet(request):
    client = _client(request)
    orders = client.orders.select_related('service', 'facility').order_by('-date')
    ctx = {
        'client': client,
        'active_orders': orders.filter(status__in=['new', 'confirmed', 'in_progress']).count(),
        'done_orders': orders.filter(status='done').count(),
        'debt': client.total_debt(),
        'recent': orders[:6],
        'facility_count': client.facilities.count(),
    }
    return render(request, 'cabinet/home.html', ctx)


@role_required('client')
def cabinet_orders(request):
    client = _client(request)
    orders = (client.orders.select_related('service', 'facility', 'team').prefetch_related('invoices')
              .order_by('-date', '-time'))
    reviewed = set(Review.objects.filter(client=client).values_list('order_id', flat=True))
    rows = [{'o': o, 'invoice': next(iter(o.invoices.all()), None), 'can_review': o.status == 'done' and o.pk not in reviewed,
             'reviewed': o.pk in reviewed} for o in orders]
    return render(request, 'cabinet/orders.html', {'rows': rows})


@role_required('client')
def cabinet_order_add(request):
    client = _client(request)
    if not client.facilities.filter(status='active').exists():
        messages.info(request, "Buyurtma berish uchun avval obyekt (tozalanadigan joy) qo'shing.")
        return redirect('cabinet_facility_add')
    form = CabinetOrderForm(request.POST or None, client=client)
    if request.method == 'POST' and form.is_valid():
        order = form.save(commit=False)
        order.client = client
        order.created_by = request.user
        order.save()
        AuditLog.log(request.user, 'create', order, details='Mijoz kabinetidan')
        messages.success(request, f'Buyurtma {order.number} qabul qilindi. Menejer uni tasdiqlaydi.')
        return redirect('cabinet_orders')
    return render(request, 'cabinet/form.html', {'form': form, 'title': 'Yangi buyurtma',
                                                 'submit': 'Buyurtma berish', 'back': reverse('cabinet_orders')})


@role_required('client')
def cabinet_facilities(request):
    client = _client(request)
    return render(request, 'cabinet/facilities.html', {'facilities': client.facilities.all()})


@role_required('client')
def cabinet_facility_add(request):
    client = _client(request)
    form = CabinetFacilityForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.client = client
        obj.save()
        AuditLog.log(request.user, 'create', obj, details='Mijoz kabinetidan')
        messages.success(request, f"«{obj.name}» obyekti qo'shildi.")
        return redirect('cabinet_facilities')
    return render(request, 'cabinet/form.html', {'form': form, 'title': "Obyekt qo'shish", 'submit': "Qo'shish",
                                                 'back': reverse('cabinet_facilities')})


@role_required('client')
def cabinet_invoices(request):
    client = _client(request)
    return render(request, 'cabinet/invoices.html', {
        'invoices': client.invoices.select_related('order').order_by('-date'), 'debt': client.total_debt()})


@role_required('client')
def cabinet_review(request, order_pk):
    client = _client(request)
    order = get_object_or_404(Order, pk=order_pk, client=client, status='done')
    if Review.objects.filter(order=order).exists():
        messages.info(request, 'Bu buyurtmani allaqachon baholagansiz.')
        return redirect('cabinet_orders')
    form = ReviewForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.order, review.client = order, client
        review.save()
        AuditLog.log(request.user, 'create', review)
        messages.success(request, 'Bahoyingiz uchun rahmat!')
        return redirect('cabinet_orders')
    return render(request, 'cabinet/form.html', {'form': form, 'title': f'Buyurtma {order.number}ni baholang',
                                                 'submit': 'Baholash', 'back': reverse('cabinet_orders')})


@role_required('client')
def cabinet_complaints(request):
    client = _client(request)
    form = ComplaintForm(request.POST or None, client=client)
    if request.method == 'POST' and form.is_valid():
        c = form.save(commit=False)
        c.client = client
        c.save()
        AuditLog.log(request.user, 'create', c, details='Mijoz kabinetidan')
        messages.success(request, 'Shikoyatingiz qabul qilindi. Tez orada ko\'rib chiqamiz.')
        return redirect('cabinet_complaints')
    return render(request, 'cabinet/complaints.html', {
        'form': form, 'complaints': client.complaints.select_related('order').order_by('-date')})
