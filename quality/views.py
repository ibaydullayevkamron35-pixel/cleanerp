from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg, Count
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.models import AuditLog
from core.permissions import section_required
from core.utils import badge_cell, section

from .forms import DEFAULT_CRITERIA, InspectionForm, InspectionItemForm, ItemFormSet
from .models import Inspection, InspectionItem


def inspection_detail(request, obj):
    items = [(i.criterion, i.zone.name if i.zone else None, f'{i.score} / 5', i.comment) for i in obj.items.all()]
    return {
        'summary': [
            ('Obyekt', {'v': obj.facility.name, 'url': reverse('facilities_detail', args=[obj.facility_id])}),
            ('Sana', obj.date), ('Tekshiruvchi', obj.inspector.full_name if obj.inspector else None),
            ('Buyurtma', obj.order.number if obj.order else None),
            ('Umumiy ball (%)', {'v': f'{obj.score}%', 'badge': 'success' if obj.score >= 80
                                 else ('warning' if obj.score >= 60 else 'danger')}),
            ('Izoh', obj.note),
        ],
        'sections': [section('Mezonlar bo\'yicha natija', ['Mezon', 'Zona', 'Ball', 'Izoh'], items,
                             empty="Mezonlar kiritilmagan")],
    }


def _inspection_form(request, inspection=None):
    creating = inspection is None
    if request.method == 'POST':
        form = InspectionForm(request.POST, instance=inspection)
        formset = ItemFormSet(request.POST, instance=inspection or Inspection())
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                obj = form.save(commit=False)
                if creating:
                    obj.created_by = request.user
                obj.save()
                formset.instance = obj
                formset.save()
                obj.recalc()
            AuditLog.log(request.user, 'create' if creating else 'update', obj)
            messages.success(request, 'Tekshiruv saqlandi.')
            return redirect('inspections_detail', pk=obj.pk)
    else:
        initial = {}
        if creating:
            emp = getattr(request.user, 'employee_profile', None)
            initial = {k: v for k, v in request.GET.items() if k in InspectionForm.base_fields}
            if emp:
                initial.setdefault('inspector', emp.pk)
        form = InspectionForm(instance=inspection, initial=initial)
        if creating:
            Extra = inlineformset_factory(Inspection, InspectionItem, form=InspectionItemForm,
                                          extra=len(DEFAULT_CRITERIA), can_delete=True)
            formset = Extra(instance=Inspection(), initial=[{'criterion': c, 'score': 5} for c in DEFAULT_CRITERIA])
        else:
            formset = ItemFormSet(instance=inspection)
    return render(request, 'quality/inspection_form.html', {
        'form': form, 'formset': formset, 'obj': inspection, 'mode': 'add' if creating else 'edit',
        'cancel_url': reverse('inspections_list') if creating else reverse('inspections_detail', args=[inspection.pk]),
    })


@section_required('inspections', 'edit')
def inspection_add(request):
    return _inspection_form(request)


@section_required('inspections', 'edit')
def inspection_edit(request, pk):
    return _inspection_form(request, get_object_or_404(Inspection, pk=pk))


@section_required('ratings', 'view')
def ratings(request):
    """Brigadalar va xodimlar sifat reytingi: mijoz baholari va tekshiruv ballari bo'yicha."""
    from hr.models import Employee, Team

    team_rows = []
    for team in Team.objects.select_related('foreman'):
        rv = team.orders.filter(review__isnull=False).aggregate(avg=Avg('review__rating'), n=Count('review'))
        facility_ids = list(team.facilities.values_list('pk', flat=True))
        ins = Inspection.objects.filter(facility_id__in=facility_ids).aggregate(avg=Avg('score'), n=Count('pk'))
        done = team.orders.filter(status='done').count()
        team_rows.append({
            'team': team, 'rating': rv['avg'], 'reviews': rv['n'], 'inspection': ins['avg'],
            'inspections': ins['n'], 'done': done,
            'members': team.member_count,
        })
    team_rows.sort(key=lambda r: (r['rating'] is None, -(r['rating'] or 0)))
    by_team = {r['team'].pk: r for r in team_rows}
    emp_rows = []
    for emp in Employee.objects.exclude(status='dismissed').select_related('team'):
        r = by_team.get(emp.team_id)
        emp_rows.append({'emp': emp, 'rating': r['rating'] if r else None,
                         'inspection': r['inspection'] if r else None})
    emp_rows.sort(key=lambda r: (r['rating'] is None, -(r['rating'] or 0)))
    return render(request, 'quality/ratings.html', {'team_rows': team_rows, 'emp_rows': emp_rows[:20]})
