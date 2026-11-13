"""Umumiy CRUD (ro'yxat, qo'shish, tahrirlash, o'chirish, ko'rish) generatori.

Har bir modul `Crud(...)` ni e'lon qiladi, `.patterns()` esa URL'larni qaytaradi:
    <slug>_list, <slug>_add, <slug>_edit, <slug>_delete, <slug>_detail, <slug>_export
"""
from dataclasses import dataclass, field
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import ProtectedError, Q, RestrictedError
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import BootstrapModelForm
from .models import AuditLog
from .permissions import can
from .utils import BADGE, fmt_value, raw_value_of, resolve, to_cell, xlsx_response


def default_summary(obj):
    rows = []
    for f in obj._meta.concrete_fields:
        if f.name == 'id':
            continue
        value = resolve(obj, f.name)
        rows.append((str(f.verbose_name).capitalize(), to_cell(value)))
    return rows


@dataclass
class Crud:
    slug: str
    url: str
    model: type
    section: str
    title: str
    singular: str
    columns: list
    fields: list = None
    form_class: type = None
    search: tuple = ()
    filters: list = field(default_factory=list)   # [(param, lookup, label, choices|callable)]
    select_related: tuple = ()
    ordering: tuple = ()
    allow_add: bool = True
    allow_edit: bool = True
    allow_delete: bool = True
    allow_detail: bool = True
    custom_form: bool = False       # qo'shish/tahrirlash view'lari alohida yozilgan
    export: bool = False
    detail_context: object = None   # callable(request, obj) -> dict(summary, sections, actions, title)
    scope: object = None            # callable(request, qs) -> qs
    per_page: int = 20
    hint: str = ''

    # ------------------------------------------------------------ nomlar
    def name(self, suffix):
        return f'{self.slug}_{suffix}'

    # ------------------------------------------------------------ yordamchilar
    def get_form_class(self):
        if self.form_class:
            return self.form_class
        return modelform_factory(self.model, form=BootstrapModelForm, fields=self.fields or '__all__')

    def base_qs(self, request):
        qs = self.model.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.scope:
            qs = self.scope(request, qs)
        if self.ordering:
            qs = qs.order_by(*self.ordering)
        return qs

    def filtered(self, request):
        qs = self.base_qs(request)
        q = request.GET.get('q', '').strip()
        if q and self.search:
            cond = Q()
            for f in self.search:
                cond |= Q(**{f'{f}__icontains': q})
            qs = qs.filter(cond)
        fctx = []
        for param, lookup, label, choices in self.filters:
            val = request.GET.get(param, '')
            if val:
                try:
                    qs = qs.filter(**{lookup: val})
                except (ValueError, TypeError, ValidationError):
                    val = ''
            ch = choices() if callable(choices) else choices
            fctx.append({'param': param, 'label': label, 'value': val,
                         'choices': [(str(v), l) for v, l in ch]})
        return qs, q, fctx

    def cell(self, obj, col):
        label, accessor, *opts = col
        value = resolve(obj, accessor)
        badge = None
        if 'badge' in opts:
            badge = BADGE.get(raw_value_of(obj, accessor), 'secondary')
        return {'v': fmt_value(value), 'url': None, 'badge': badge}

    def safe_next(self, request):
        nxt = request.POST.get('next') or request.GET.get('next')
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                                    require_https=request.is_secure()):
            return nxt
        return None

    def after_save_url(self, request, obj):
        nxt = self.safe_next(request)
        if nxt:
            return nxt
        if self.allow_detail:
            return reverse(self.name('detail'), args=[obj.pk])
        return reverse(self.name('list'))

    def guarded(self, mode):
        def deco(fn):
            @wraps(fn)
            def wrapper(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return redirect_to_login(request.get_full_path())
                if not can(request.user, self.section, mode):
                    raise PermissionDenied
                return fn(request, *args, **kwargs)
            return wrapper
        return deco

    def base_ctx(self, request):
        return {
            'cfg': self,
            'can_edit': can(request.user, self.section, 'edit'),
        }

    # ------------------------------------------------------------ view'lar
    def make_list(self):
        @self.guarded('view')
        def list_view(request):
            qs, q, fctx = self.filtered(request)
            page_obj = Paginator(qs, self.per_page).get_page(request.GET.get('page'))
            ctx = self.base_ctx(request)
            edit = ctx['can_edit']
            rows = []
            for obj in page_obj:
                cells = [self.cell(obj, c) for c in self.columns]
                detail = reverse(self.name('detail'), args=[obj.pk]) if self.allow_detail else None
                edit_url = reverse(self.name('edit'), args=[obj.pk]) if (self.allow_edit and edit) else None
                if cells:
                    cells[0]['url'] = detail or edit_url
                rows.append({
                    'obj': obj, 'cells': cells, 'detail': detail, 'edit': edit_url,
                    'delete': reverse(self.name('delete'), args=[obj.pk]) if (self.allow_delete and edit) else None,
                })
            params = request.GET.copy()
            params.pop('page', None)
            ctx.update({
                'headers': [c[0] for c in self.columns],
                'rows': rows,
                'page_obj': page_obj,
                'q': q,
                'filters': fctx,
                'query': params.urlencode(),
                'has_filter': bool(q or any(f['value'] for f in fctx)),
                'add_url': reverse(self.name('add')) if (self.allow_add and edit) else None,
                'export_url': reverse(self.name('export')) if self.export else None,
                'show_actions': any(r['edit'] or r['delete'] for r in rows),
                'total': page_obj.paginator.count,
            })
            return render(request, 'crud/list.html', ctx)
        return list_view

    def make_export(self):
        @self.guarded('view')
        def export_view(request):
            qs, _, _ = self.filtered(request)
            headers = [c[0] for c in self.columns]
            rows = [[self.cell(o, c)['v'] for c in self.columns] for o in qs]
            return xlsx_response(self.slug, self.title, headers, rows)
        return export_view

    def _save(self, request, form, created):
        obj = form.save(commit=False)
        if created and hasattr(obj, 'created_by_id') and obj.created_by_id is None:
            obj.created_by = request.user
        obj.save()
        form.save_m2m()
        AuditLog.log(request.user, 'create' if created else 'update', obj,
                     details='' if created else ', '.join(form.changed_data))
        messages.success(request, f"{self.singular} saqlandi.")
        return redirect(self.after_save_url(request, obj))

    def make_add(self):
        @self.guarded('edit')
        def add_view(request):
            Form = self.get_form_class()
            if request.method == 'POST':
                form = Form(request.POST, request.FILES)
                if form.is_valid():
                    return self._save(request, form, True)
            else:
                initial = {k: v for k, v in request.GET.items() if k in Form.base_fields}
                form = Form(initial=initial)
            ctx = self.base_ctx(request)
            ctx.update({'form': form, 'mode': 'add', 'next': self.safe_next(request) or '',
                        'cancel_url': self.safe_next(request) or reverse(self.name('list'))})
            return render(request, 'crud/form.html', ctx)
        return add_view

    def make_edit(self):
        @self.guarded('edit')
        def edit_view(request, pk):
            obj = get_object_or_404(self.base_qs(request), pk=pk)
            Form = self.get_form_class()
            if request.method == 'POST':
                form = Form(request.POST, request.FILES, instance=obj)
                if form.is_valid():
                    return self._save(request, form, False)
            else:
                form = Form(instance=obj)
            back = self.safe_next(request) or (
                reverse(self.name('detail'), args=[obj.pk]) if self.allow_detail else reverse(self.name('list')))
            ctx = self.base_ctx(request)
            ctx.update({'form': form, 'obj': obj, 'mode': 'edit', 'next': self.safe_next(request) or '',
                        'cancel_url': back})
            return render(request, 'crud/form.html', ctx)
        return edit_view

    def make_delete(self):
        @self.guarded('edit')
        def delete_view(request, pk):
            obj = get_object_or_404(self.base_qs(request), pk=pk)
            back = self.safe_next(request) or reverse(self.name('list'))
            if request.method == 'POST':
                label = str(obj)
                try:
                    with transaction.atomic():
                        AuditLog.log(request.user, 'delete', obj)
                        obj.delete()
                except (ProtectedError, RestrictedError):
                    messages.error(request, f"«{label}» bilan bog'liq yozuvlar mavjud, shuning uchun o'chirib bo'lmaydi. "
                                            f"Avval bog'liq yozuvlarni o'chiring yoki holatini o'zgartiring.")
                    return redirect(back)
                messages.success(request, f"«{label}» o'chirildi.")
                return redirect(back)
            ctx = self.base_ctx(request)
            ctx.update({'obj': obj, 'cancel_url': back, 'next': self.safe_next(request) or ''})
            return render(request, 'crud/confirm_delete.html', ctx)
        return delete_view

    def make_detail(self):
        @self.guarded('view')
        def detail_view(request, pk):
            obj = get_object_or_404(self.base_qs(request), pk=pk)
            ctx = self.base_ctx(request)
            ctx.update({'obj': obj, 'title': str(obj),
                        'edit_url': reverse(self.name('edit'), args=[obj.pk])
                        if (self.allow_edit and ctx['can_edit']) else None,
                        'delete_url': reverse(self.name('delete'), args=[obj.pk])
                        if (self.allow_delete and ctx['can_edit']) else None,
                        'list_url': reverse(self.name('list'))})
            if self.detail_context:
                ctx.update(self.detail_context(request, obj))
            ctx.setdefault('summary', default_summary(obj))
            ctx['summary'] = [(label, to_cell(v)) for label, v in ctx['summary']]
            ctx.setdefault('sections', [])
            ctx.setdefault('actions', [])
            return render(request, 'crud/detail.html', ctx)
        return detail_view

    # ------------------------------------------------------------ URL'lar
    def patterns(self):
        u = self.url
        urls = [path(f'{u}/', self.make_list(), name=self.name('list'))]
        if self.export:
            urls.append(path(f'{u}/eksport/', self.make_export(), name=self.name('export')))
        if self.allow_add and not self.custom_form:
            urls.append(path(f'{u}/yangi/', self.make_add(), name=self.name('add')))
        if self.allow_edit and not self.custom_form:
            urls.append(path(f'{u}/<int:pk>/tahrirlash/', self.make_edit(), name=self.name('edit')))
        if self.allow_delete:
            urls.append(path(f'{u}/<int:pk>/ochirish/', self.make_delete(), name=self.name('delete')))
        if self.allow_detail:
            urls.append(path(f'{u}/<int:pk>/', self.make_detail(), name=self.name('detail')))
        return urls
