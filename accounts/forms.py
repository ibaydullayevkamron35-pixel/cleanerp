from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from core.forms import BootstrapForm, BootstrapModelForm, style_form

from .models import User


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)
        self.fields['username'].label = 'Login'
        self.fields['password'].label = 'Parol'
        self.fields['username'].widget.attrs.update({'autofocus': True, 'autocomplete': 'username'})


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class UserForm(BootstrapModelForm):
    """Administrator foydalanuvchi yaratadi/tahrirlaydi."""
    password = forms.CharField(
        label='Parol', required=False, widget=forms.PasswordInput(render_value=False),
        help_text="Tahrirlashda bo'sh qoldirilsa, parol o'zgarmaydi.")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'phone', 'email', 'role', 'is_active', 'photo']

    def clean_password(self):
        pw = self.cleaned_data.get('password')
        if not self.instance.pk and not pw:
            raise forms.ValidationError('Yangi foydalanuvchi uchun parol kiriting.')
        if pw:
            validate_password(pw, self.instance)
        return pw

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('password')
        if pw:
            user.set_password(pw)
        user.is_staff = user.is_superuser = (user.role == User.Role.ADMIN)
        if commit:
            user.save()
        return user


class ProfileForm(BootstrapModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email', 'photo']


class RegisterForm(BootstrapForm):
    """Mijozning o'zini ro'yxatdan o'tkazishi."""
    kind = forms.ChoiceField(label='Mijoz turi', initial='individual',
                             choices=[('individual', 'Jismoniy shaxs'), ('legal', 'Yuridik shaxs')])
    name = forms.CharField(label='F.I.Sh. yoki kompaniya nomi', max_length=200)
    phone = forms.CharField(label='Telefon', max_length=30)
    username = forms.CharField(label='Login', max_length=150)
    password1 = forms.CharField(label='Parol', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Parolni takrorlang', widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Bu login band, boshqasini tanlang.')
        return username

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2:
            if p1 != p2:
                self.add_error('password2', 'Parollar bir xil emas.')
            else:
                try:
                    validate_password(p1)
                except forms.ValidationError as e:
                    self.add_error('password1', e)
        return data

    @transaction.atomic
    def save(self):
        from crm.models import Client

        d = self.cleaned_data
        user = User.objects.create_user(
            username=d['username'], password=d['password1'], first_name=d['name'][:150],
            phone=d['phone'], role=User.Role.CLIENT)
        Client.objects.create(kind=d['kind'], name=d['name'], phone=d['phone'], user=user)
        return user
