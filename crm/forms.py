from django import forms
from django.urls import reverse

from core.forms import BootstrapModelForm

from .models import Contract


class ContractForm(BootstrapModelForm):
    """Shartnoma: mijoz tanlanganda faqat uning obyektlari (ofis, bino va h.k.) ko'rinadi."""

    class Meta:
        model = Contract
        fields = ['client', 'number', 'date', 'end_date', 'amount', 'status', 'facilities', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fac = self.fields['facilities']
        fac.widget.attrs['data-filter-by'] = 'id_client'
        fac.widget.attrs['data-quick-url'] = reverse('facilities_quick_add')
        fac.help_text = "Avval mijozni tanlang, so'ng shartnoma qamrab oladigan obyektlarni belgilang."

    def clean(self):
        data = super().clean()
        client, facs = data.get('client'), data.get('facilities')
        if client and facs:
            wrong = [f.name for f in facs if f.client_id != client.pk]
            if wrong:
                self.add_error('facilities', "Bu obyektlar tanlangan mijozga tegishli emas: " + ', '.join(wrong))
        return data
