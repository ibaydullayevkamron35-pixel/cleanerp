from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import path, reverse_lazy

from core.crud import Crud

from . import views
from .forms import LoginForm, StyledPasswordChangeForm, UserForm
from .models import User

users = Crud(
    slug='users', url='foydalanuvchilar', model=User, section='users', title='Foydalanuvchilar',
    singular='Foydalanuvchi',
    columns=[('Login', 'username'), ('F.I.Sh.', 'display_name'), ('Rol', 'role'), ('Telefon', 'phone'),
             ('Faol', 'is_active')],
    form_class=UserForm,
    search=('username', 'first_name', 'last_name', 'phone', 'email'),
    filters=[('role', 'role', 'Rol', User.Role.choices)],
    allow_detail=False, ordering=('username',),
)

urlpatterns = [
    path('yonalish/', views.home, name='home'),
    path('kirish/', LoginView.as_view(template_name='accounts/login.html', authentication_form=LoginForm,
                                      redirect_authenticated_user=True), name='login'),
    path('chiqish/', LogoutView.as_view(), name='logout'),
    path('royxatdan-otish/', views.register, name='register'),
    path('profil/', views.profile, name='profile'),
    path('parol/', PasswordChangeView.as_view(template_name='accounts/password_change.html',
                                              form_class=StyledPasswordChangeForm,
                                              success_url=reverse_lazy('profile')), name='password_change'),
] + users.patterns()
