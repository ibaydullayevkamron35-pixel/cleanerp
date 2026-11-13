from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Umumiy'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from .models import AuditLog

        def on_login(sender, request, user, **kwargs):
            AuditLog.log(user, 'login', details='Tizimga kirdi')

        user_logged_in.connect(on_login, dispatch_uid='cleanerp_login_audit')
