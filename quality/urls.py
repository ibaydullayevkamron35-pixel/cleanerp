from django.urls import path

from core.crud import Crud

from . import views
from .models import Complaint, Inspection, Review

inspections = Crud(
    slug='inspections', url='tekshiruvlar', model=Inspection, section='inspections', title='Tekshiruvlar',
    singular='Tekshiruv',
    columns=[('Sana', 'date'), ('Obyekt', 'facility'), ('Tekshiruvchi', 'inspector'), ('Ball (%)', 'score')],
    search=('facility__name', 'inspector__full_name', 'note'),
    select_related=('facility', 'inspector'), custom_form=True, detail_context=views.inspection_detail,
)

complaints = Crud(
    slug='complaints', url='shikoyatlar', model=Complaint, section='complaints', title='Shikoyatlar',
    singular='Shikoyat',
    columns=[('Sana', 'date'), ('Mijoz', 'client'), ('Mavzu', 'subject'), ("Mas'ul", 'assignee'),
             ('Holat', 'status', 'badge')],
    fields=['client', 'order', 'subject', 'content', 'date', 'status', 'assignee', 'resolution'],
    search=('subject', 'content', 'client__name'),
    filters=[('status', 'status', 'Holat', Complaint.Status.choices)],
    select_related=('client', 'assignee'),
)

reviews = Crud(
    slug='reviews', url='baholar', model=Review, section='reviews', title='Mijoz baholari', singular='Baho',
    columns=[('Sana', 'date'), ('Buyurtma', 'order'), ('Mijoz', 'client'), ('Ball (1-5)', 'rating'),
             ('Izoh', 'comment')],
    fields=['order', 'client', 'rating', 'date', 'comment'],
    search=('client__name', 'comment', 'order__number'),
    filters=[('rating', 'rating', 'Ball', [(i, str(i)) for i in range(1, 6)])],
    select_related=('client', 'order'), allow_detail=False,
)

urlpatterns = inspections.patterns() + complaints.patterns() + reviews.patterns() + [
    path('tekshiruvlar/yangi/', views.inspection_add, name='inspections_add'),
    path('tekshiruvlar/<int:pk>/tahrirlash/', views.inspection_edit, name='inspections_edit'),
    path('reyting/', views.ratings, name='ratings'),
]
