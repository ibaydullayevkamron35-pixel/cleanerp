from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Muhim amallar jurnali: kim, nima, qachon o'zgartirgan."""

    class Action(models.TextChoices):
        CREATE = 'create', "Qo'shildi"
        UPDATE = 'update', "O'zgartirildi"
        DELETE = 'delete', "O'chirildi"
        LOGIN = 'login', 'Kirish'
        OTHER = 'other', 'Boshqa amal'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField('Amal', max_length=10, choices=Action.choices)
    model_name = models.CharField('Bo\'lim', max_length=100, blank=True)
    object_id = models.CharField('Yozuv ID', max_length=50, blank=True)
    object_repr = models.CharField('Yozuv', max_length=255, blank=True)
    details = models.TextField('Tafsilot', blank=True)
    created_at = models.DateTimeField('Vaqt', auto_now_add=True)

    class Meta:
        verbose_name = 'Amal jurnali'
        verbose_name_plural = 'Amallar jurnali'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()}: {self.object_repr}'

    @classmethod
    def log(cls, user, action, obj=None, details='', model_name=None):
        if user is not None and not getattr(user, 'is_authenticated', False):
            user = None
        name = model_name or (obj._meta.verbose_name if obj is not None else '')
        return cls.objects.create(
            user=user,
            action=action,
            model_name=str(name)[:100],
            object_id=str(getattr(obj, 'pk', '') or '')[:50],
            object_repr=(str(obj) if obj is not None else '')[:255],
            details=details,
        )
