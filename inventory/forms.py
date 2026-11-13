from core.forms import BootstrapModelForm

from .models import InventoryItem, StockMovement


class MovementForm(BootstrapModelForm):
    class Meta:
        model = StockMovement
        fields = ['item', 'kind', 'quantity', 'date', 'facility', 'employee', 'supplier', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = [c for c in StockMovement.Kind.choices if c[0] != 'adjust']
        self.fields['item'].queryset = InventoryItem.objects.filter(is_active=True)
        self.fields['quantity'].widget.attrs['min'] = '0.01'
