from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegisterForm

ROLE_HOME = {
    'admin': 'dashboard', 'director': 'dashboard', 'manager': 'dashboard',
    'foreman': 'my_tasks', 'cleaner': 'my_tasks',
    'accountant': 'invoices_list', 'storekeeper': 'inventory_list',
    'client': 'cabinet',
}


def home(request):
    """Kirgandan keyin rolga mos bosh sahifaga yo'naltiradi."""
    if not request.user.is_authenticated:
        return redirect('landing')
    return redirect(ROLE_HOME.get(request.user.role, 'landing'))


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, "Ro'yxatdan o'tdingiz. Shaxsiy kabinetga xush kelibsiz!")
        return redirect('cabinet')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profil ma'lumotlari saqlandi.")
        return redirect('profile')
    base = 'cabinet/base.html' if request.user.role == 'client' else 'base_panel.html'
    return render(request, 'accounts/profile.html', {'form': form, 'base_template': base})
