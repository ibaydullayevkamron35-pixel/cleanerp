from django.conf import settings
from django.urls import reverse

from .permissions import MENU, PERMS, can


def nav(request):
    """Barcha shablonlarga: kompaniya ma'lumoti, rolga mos menyu va ruxsatlar."""
    ctx = {'COMPANY': settings.COMPANY}
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        match = getattr(request, 'resolver_match', None)
        current = (match.url_name if match and match.url_name else '') or ''
        cur_prefix = current.split('_')[0]
        groups = []
        for title, items in MENU:
            entries = []
            for section, label, icon, url_name in items:
                if can(user, section, 'view'):
                    entries.append({
                        'label': label,
                        'icon': icon,
                        'url': reverse(url_name),
                        'active': url_name.split('_')[0] == cur_prefix,
                    })
            if entries:
                groups.append({'title': title, 'items': entries})
        ctx['nav_groups'] = groups
        ctx['can'] = {s: {'view': can(user, s, 'view'), 'edit': can(user, s, 'edit')} for s in PERMS}
    return ctx
