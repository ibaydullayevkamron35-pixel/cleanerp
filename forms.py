from django import forms

from .widgets import CheckboxDropdown


def style_form(form):
    """Barcha maydonlarga Bootstrap klasslari va to'g'ri HTML5 kiritish turlarini beradi."""
    for field in form.fields.values():
        w = field.widget
        if type(w) is forms.SelectMultiple:
            new = CheckboxDropdown(attrs=w.attrs)
            new.choices = field.choices
            new.is_required = field.required
            field.widget = w = new
        if isinstance(w, forms.CheckboxInput):
            cls = 'form-check-input'
        elif isinstance(w, CheckboxDropdown):
            cls = ''
        elif isinstance(w, (forms.Select, forms.SelectMultiple)):
            cls = 'form-select'
        elif isinstance(w, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
            cls = ''
        else:
            cls = 'form-control'
        if cls:
            w.attrs['class'] = (w.attrs.get('class', '') + ' ' + cls).strip()
        if isinstance(w, forms.DateInput):
            w.input_type = 'date'
            w.format = '%Y-%m-%d'
        elif isinstance(w, forms.TimeInput):
            w.input_type = 'time'
            w.format = '%H:%M'
        if isinstance(w, forms.Textarea):
            w.attrs.setdefault('rows', 3)


class BootstrapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)
