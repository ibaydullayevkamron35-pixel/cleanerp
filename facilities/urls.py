from core.crud import Crud

from . import views
from .models import CleaningSchedule, Facility, Zone

facilities = Crud(
    slug='facilities', url='obyektlar', model=Facility, section='facilities', title='Obyektlar', singular='Obyekt',
    columns=[('Nomi', 'name'), ('Mijoz', 'client'), ('Turi', 'kind'), ('Manzil', 'address'),
             ('Maydon (m²)', 'area'), ('Holat', 'status', 'badge')],
    fields=['client', 'name', 'kind', 'address', 'area', 'floors', 'requirements', 'instructions', 'status',
            'teams', 'employees'],
    search=('name', 'address', 'client__name'),
    filters=[('kind', 'kind', 'Turi', Facility.Kind.choices), ('status', 'status', 'Holat', Facility.Status.choices)],
    select_related=('client',), export=True, detail_context=views.facility_detail,
)

zones = Crud(
    slug='zones', url='zonalar', model=Zone, section='facilities', title='Zonalar', singular='Zona',
    columns=[('Zona', 'name'), ('Obyekt', 'facility'), ('Maydon (m²)', 'area'), ('Tozalash turi', 'cleaning_type')],
    fields=['facility', 'name', 'area', 'cleaning_type'],
    search=('name', 'facility__name'), select_related=('facility',), allow_detail=False,
)

schedules = Crud(
    slug='schedules', url='jadvallar', model=CleaningSchedule, section='facilities',
    title='Tozalash jadvallari', singular='Jadval',
    columns=[('Obyekt', 'facility'), ('Davriylik', 'frequency'), ('Xizmat', 'service'), ('Qachon', 'when'),
             ('Faol', 'is_active')],
    fields=['facility', 'service', 'frequency', 'weekday', 'month_day', 'time', 'is_active', 'note'],
    search=('facility__name', 'service__name'), select_related=('facility', 'service'), allow_detail=False,
)

urlpatterns = facilities.patterns() + zones.patterns() + schedules.patterns()
