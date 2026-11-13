from django import forms

from core.forms import BootstrapModelForm
from crm.models import Lead
from facilities.models import Facility
from orders.models import Order, ServiceType
from quality.models import Complaint, Review


class LeadForm(BootstrapModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'phone', 'service', 'address', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = ServiceType.objects.filter(is_active=True)
        self.fields['service'].empty_label = 'Xizmatni tanlang (ixtiyoriy)'
        self.fields['name'].widget.attrs['placeholder'] = 'Ismingiz'
        self.fields['phone'].widget.attrs['placeholder'] = '+998 __ ___ __ __'
        self.fields['address'].widget.attrs['placeholder'] = "Obyekt manzili (ixtiyoriy)"
        self.fields['message'].widget.attrs['placeholder'] = "Qo'shimcha xabar (ixtiyoriy)"


class CabinetOrderForm(BootstrapModelForm):
    class Meta:
        model = Order
        fields = ['facility', 'service', 'date', 'time', 'quantity', 'recurrence', 'recurrence_end', 'note']

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.instance.client = client
        self.fields['facility'].queryset = Facility.objects.filter(client=client, status='active')
        self.fields['service'].queryset = ServiceType.objects.filter(is_active=True)
        self.fields['quantity'].required = False
        self.fields['quantity'].help_text = "Bo'sh qoldirsangiz: m² narxida obyekt maydoni, boshqalarda 1 olinadi."

    def clean(self):
        data = super().clean()
        if data.get('quantity') in (None, ''):
            service, facility = data.get('service'), data.get('facility')
            if service and facility and service.unit == ServiceType.Unit.M2 and facility.area:
                data['quantity'] = facility.area
            else:
                data['quantity'] = 1
        return data


class CabinetFacilityForm(BootstrapModelForm):
    class Meta:
        model = Facility
        fields = ['name', 'kind', 'address', 'area', 'floors', 'requirements']


class ReviewForm(BootstrapModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {'rating': forms.Select(choices=[(i, f'{i} — {"★" * i}') for i in range(5, 0, -1)])}


class ComplaintForm(BootstrapModelForm):
    class Meta:
        model = Complaint
        fields = ['order', 'subject', 'content']

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].queryset = Order.objects.filter(client=client)
        self.fields['order'].required = False
        self.fields['order'].empty_label = 'Buyurtmani tanlang (ixtiyoriy)'
