from django.urls import path  # noqa: F401

from .crud import Crud
from .models import AuditLog

audit = Crud(
    slug='audit', url='jurnal', model=AuditLog, section='audit',
    title='Amallar jurnali', singular='Yozuv',
    columns=[('Vaqt', 'created_at'), ('Foydalanuvchi', 'user'), ('Amal', 'action', 'badge'),
             ("Bo'lim", 'model_name'), ('Yozuv', 'object_repr'), ('Tafsilot', 'details')],
    search=('object_repr', 'model_name', 'user__username', 'details'),
    filters=[('action', 'action', 'Amal', AuditLog.Action.choices)],
    select_related=('user',), ordering=('-created_at',),
    allow_add=False, allow_edit=False, allow_delete=False, allow_detail=False,
    per_page=30,
)

urlpatterns = audit.patterns()
