from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        DIRECTOR = 'director', 'Rahbar (direktor)'
        MANAGER = 'manager', 'Menejer'
        FOREMAN = 'foreman', 'Brigadir (nazoratchi)'
        CLEANER = 'cleaner', 'Tozalovchi xodim'
        ACCOUNTANT = 'accountant', 'Buxgalter'
        STOREKEEPER = 'storekeeper', 'Omborchi'
        CLIENT = 'client', 'Mijoz'

    role = models.CharField('Rol', max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField('Telefon', max_length=30, blank=True)
    photo = models.ImageField('Rasm', upload_to='users/', blank=True, null=True)

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'

    def save(self, *args, **kwargs):
        # createsuperuser orqali yaratilganlar avtomatik administrator bo'ladi
        if self.is_superuser and self.role == self.Role.CLIENT:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT

    def __str__(self):
        return self.display_name
