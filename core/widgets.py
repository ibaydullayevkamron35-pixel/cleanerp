from django import forms
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


QUICK = (
    '<div class="dd-quick border-top mt-1 pt-2 px-2 pb-1">'
    '<button type="button" class="btn btn-sm btn-outline-primary dd-quick-open">'
    '<i class="bi bi-plus-lg me-1"></i>Yangi obyekt (ofis) qo\'shish</button>'
    '<div class="dd-quick-form mt-2" hidden>'
    '<input class="form-control form-control-sm mb-2 q-name" placeholder="Nomi (masalan: Chilonzor filiali)">'
    '<input class="form-control form-control-sm mb-2 q-address" placeholder="Manzil">'
    '<select class="form-select form-select-sm mb-2 q-kind">'
    '<option value="office">Ofis</option><option value="home">Turar joy / uy</option>'
    '<option value="mall">Savdo markazi</option><option value="school">Maktab / bog\'cha</option>'
    '<option value="hospital">Shifoxona</option><option value="hotel">Mehmonxona</option>'
    '<option value="warehouse">Ombor / ishlab chiqarish</option><option value="other">Boshqa</option></select>'
    '<div class="text-danger small mb-1 q-err" hidden></div>'
    '<button type="button" class="btn btn-sm btn-primary dd-quick-save">Qo\'shish</button></div></div>'
)


class CheckboxDropdown(forms.SelectMultiple):
    """Ko'p tanlov: yopiq dropdown, ichida galochkali ro'yxat.

    Tanlanganlar tugma ustida nomi bilan ko'rinadi, qolganlari ro'yxat ochilmaguncha yopiq turadi.
    """

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        btn_id = attrs.get('id', f'id_{name}')
        filter_by = attrs.get('data-filter-by', '')
        quick_url = attrs.get('data-quick-url', '')
        selected = {str(v) for v in (value or [])}
        items = []
        for _group, options, _idx in self.optgroups(name, list(selected), attrs):
            for opt in options:
                val = str(opt['value'])
                if val == '':
                    continue
                inst = getattr(opt['value'], 'instance', None)
                owner = getattr(inst, 'client_id', '') if inst is not None else ''
                items.append(format_html(
                    '<label class="dropdown-item dd-item d-flex align-items-center gap-2" data-owner="{}">'
                    '<input class="form-check-input mt-0" type="checkbox" name="{}" value="{}"{}> <span>{}</span></label>',
                    owner, name, val, mark_safe(' checked') if val in selected else '', opt['label']))
        return format_html(
            '<div class="dd-multi dropdown" data-filter-by="{}" data-quick-url="{}">'
            '<button type="button" id="{}" class="form-select text-start dd-toggle" data-bs-toggle="dropdown" '
            'data-bs-auto-close="outside" aria-expanded="false"><span class="dd-label text-muted">Tanlang</span></button>'
            '<div class="dropdown-menu w-100 p-1 dd-menu">{}<div class="dd-empty text-muted small px-3 py-2" hidden>'
            "Ro'yxat bo'sh</div>{}</div></div>",
            filter_by, quick_url, btn_id, mark_safe(''.join(items)), mark_safe(QUICK if quick_url else ''))

    def value_from_datadict(self, data, files, name):
        getter = data.getlist if hasattr(data, 'getlist') else data.get
        return getter(name)

    def id_for_label(self, id_):
        return id_
