from django import forms
from django.forms import inlineformset_factory

from core.forms import BootstrapModelForm, style_form

from .models import Inspection, InspectionItem

DEFAULT_CRITERIA = ['Polni tozalash', 'Derazalar va oynalar', 'Hojatxona va sanitariya', 'Mebel va yuzalar',
                    "Axlat yig'ish", 'Hid va havo sifati']


class InspectionForm(BootstrapModelForm):
    class Meta:
        model = Inspection
        fields = ['facility', 'order', 'inspector', 'date', 'note']


class InspectionItemForm(forms.ModelForm):
    class Meta:
        model = InspectionItem
        fields = ['criterion', 'score', 'comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)
        self.fields['score'].widget.attrs.update({'min': 1, 'max': 5})


ItemFormSet = inlineformset_factory(Inspection, InspectionItem, form=InspectionItemForm, extra=0, can_delete=True,
                                    min_num=1, validate_min=True)
