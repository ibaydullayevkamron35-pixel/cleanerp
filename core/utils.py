"""Umumiy yordamchi funksiyalar: formatlash, eksport (Excel/PDF), davr tanlash."""
import calendar
import datetime
import inspect
import os
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

# Holat qiymatlari -> Bootstrap rangi
BADGE = {
    'new': 'primary', 'confirmed': 'info', 'in_progress': 'warning', 'done': 'success', 'cancelled': 'secondary',
    'unpaid': 'danger', 'partial': 'warning', 'paid': 'success',
    'active': 'success', 'inactive': 'secondary', 'draft': 'secondary', 'expired': 'danger', 'terminated': 'secondary',
    'present': 'success', 'late': 'warning', 'absent': 'danger', 'leave': 'info',
    'vacation': 'info', 'dismissed': 'secondary',
    'resolved': 'success', 'closed': 'secondary',
    'contacted': 'info', 'converted': 'success', 'rejected': 'secondary',
    'in': 'success', 'out': 'danger', 'return': 'info', 'adjust': 'secondary',
    'create': 'success', 'update': 'warning', 'delete': 'danger', 'login': 'info', 'other': 'secondary',
}


def money(value):
    """1250000 -> '1 250 000', 12.5 -> '12.50'"""
    if value is None:
        return '—'
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    if d == d.to_integral_value():
        return f'{int(d):,}'.replace(',', ' ')
    return f'{d:,.2f}'.replace(',', ' ')


def fmt_value(v):
    if v is None or v == '':
        return '—'
    if isinstance(v, bool):
        return 'Ha' if v else "Yo'q"
    if isinstance(v, (Decimal, float)):
        return money(v)
    if isinstance(v, datetime.datetime):
        if timezone.is_aware(v):
            v = timezone.localtime(v)
        return v.strftime('%d.%m.%Y %H:%M')
    if isinstance(v, datetime.date):
        return v.strftime('%d.%m.%Y')
    if isinstance(v, datetime.time):
        return v.strftime('%H:%M')
    return str(v)


def resolve(obj, path, display=True):
    """'client.name' kabi yo'l bo'yicha qiymatni oladi. choices bo'lsa — o'qiladigan nomini qaytaradi.
    Metod bo'lsa chaqiriladi (property ham ishlaydi)."""
    cur = obj
    for part in path.split('.'):
        if cur is None:
            return None
        field = None
        try:
            field = cur._meta.get_field(part)
        except Exception:
            field = None
        if display and field is not None and getattr(field, 'choices', None) and not field.is_relation:
            cur = getattr(cur, f'get_{part}_display')()
        else:
            cur = getattr(cur, part)
            if inspect.ismethod(cur):
                cur = cur()
    return cur


def raw_value_of(obj, path):
    """choices'ning o'qiladigan nomisiz, asl qiymati (badge rangi uchun)."""
    return resolve(obj, path, display=False)


def to_cell(value, url=None, badge=None):
    """Shablon uchun uyacha: {'v': matn, 'url': havola, 'badge': rang}."""
    if isinstance(value, dict):
        d = dict(value)
        v = d.get('v')
        d['v'] = v if isinstance(v, str) else fmt_value(v)
        d.setdefault('url', None)
        d.setdefault('badge', None)
        return d
    return {'v': fmt_value(value), 'url': url, 'badge': badge}


def badge_cell(raw, text):
    return {'v': text, 'url': None, 'badge': BADGE.get(raw, 'secondary')}


def section(title, headers, rows, add_url=None, add_label="Qo'shish", empty='Ma\'lumot yo\'q'):
    """Detail sahifasidagi jadval bo'limi."""
    return {
        'title': title,
        'headers': headers,
        'rows': [[to_cell(c) for c in row] for row in rows],
        'add_url': add_url,
        'add_label': add_label,
        'empty': empty,
    }


# ---------------------------------------------------------------- davr tanlash
PERIODS = [('day', 'Bugun'), ('week', 'Bu hafta'), ('month', 'Bu oy'), ('year', 'Bu yil')]


def get_period(request):
    """GET parametrlardan davrni aniqlaydi -> (boshlanish, tugash, kod)."""
    today = timezone.localdate()
    code = request.GET.get('period', 'month')
    df, dt = request.GET.get('from'), request.GET.get('to')
    if df and dt:
        try:
            start, end = datetime.date.fromisoformat(df), datetime.date.fromisoformat(dt)
            if start <= end:
                return start, end, 'custom'
        except ValueError:
            pass
    if code == 'day':
        return today, today, 'day'
    if code == 'week':
        start = today - datetime.timedelta(days=today.weekday())
        return start, start + datetime.timedelta(days=6), 'week'
    if code == 'year':
        return datetime.date(today.year, 1, 1), datetime.date(today.year, 12, 31), 'year'
    last = calendar.monthrange(today.year, today.month)[1]
    return today.replace(day=1), today.replace(day=last), 'month'


def add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return datetime.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


# ---------------------------------------------------------------- Excel / PDF
def archive_to_storage(path, data):
    """Yaratilgan faylni (PDF/Excel) S3 ga arxivlaydi. S3 sozlanmagan bo'lsa yoki xato bo'lsa, indamay o'tadi."""
    from django.conf import settings
    if not getattr(settings, 'AWS_STORAGE_BUCKET_NAME', ''):
        return None
    try:
        import datetime as _dt
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        stamp = _dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        return default_storage.save(f'{path}-{stamp}', ContentFile(data))
    except Exception:  # arxivlash asosiy ishni buzmasligi kerak
        import logging
        logging.getLogger(__name__).exception('S3 ga arxivlashda xato')
        return None


def xlsx_response(filename, title, headers, rows):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    safe = ''.join(' ' if ch in '\\/?*[]:' else ch for ch in (title or 'Hisobot')).strip("' ")
    ws.title = (safe or 'Hisobot')[:31]
    ws.append(list(headers))
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='0F766E')
        cell.alignment = Alignment(vertical='center')
    for row in rows:
        ws.append([fmt_plain(c) for c in row])
    for i, h in enumerate(headers, start=1):
        width = max([len(str(h))] + [len(str(fmt_plain(r[i - 1]))) for r in rows if len(r) >= i] + [8])
        ws.column_dimensions[get_column_letter(i)].width = min(width + 2, 50)
    ws.freeze_panes = 'A2'
    buf = BytesIO()
    wb.save(buf)
    archive_to_storage(f'reports/{filename}.xlsx', buf.getvalue())
    resp = HttpResponse(buf.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return resp


def fmt_plain(c):
    if isinstance(c, dict):
        return c.get('v', '')
    if isinstance(c, (Decimal, float)):
        return float(c)
    if isinstance(c, datetime.datetime):
        return fmt_value(c)
    if isinstance(c, (datetime.date, datetime.time)):
        return fmt_value(c)
    return '' if c is None else c


def pdf_font():
    """Unicode shrift topilsa (DejaVu), bo'lmasa Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        ('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        ('DejaVuSans', '/usr/share/fonts/dejavu/DejaVuSans.ttf'),
        ('DejaVuSans', 'C:/Windows/Fonts/arial.ttf'),
        ('DejaVuSans', '/Library/Fonts/Arial.ttf'),
        ('DejaVuSans', '/System/Library/Fonts/Supplemental/Arial.ttf'),
    ]
    for name, path in candidates:
        if os.path.exists(path):
            try:
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return 'Helvetica'


def pdf_table_response(filename, title, headers, rows, subtitle='', footer_rows=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font = pdf_font()
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=styles['Title'], fontName=font, fontSize=16, alignment=0)
    small = ParagraphStyle('small', parent=styles['Normal'], fontName=font, fontSize=9, textColor=colors.grey)
    cell = ParagraphStyle('cell', parent=styles['Normal'], fontName=font, fontSize=8, leading=10)
    head = ParagraphStyle('head', parent=cell, textColor=colors.white)

    def P(v, style=cell):
        return Paragraph(escape(str(fmt_value(fmt_plain(v)))), style)

    data = [[P(h, head) for h in headers]]
    data += [[P(c) for c in row] for row in rows]
    for row in footer_rows or []:
        data.append([P(c) for c in row])

    buf = BytesIO()
    wide = len(headers) > 6
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4) if wide else A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=title)
    table = Table(data, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]
    table.setStyle(TableStyle(style))
    story = [Paragraph(escape(title), h1)]
    if subtitle:
        story.append(Paragraph(escape(subtitle), small))
    story += [Spacer(1, 6 * mm), table]
    doc.build(story)
    archive_to_storage(f'reports/{filename}.pdf', buf.getvalue())
    resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    return resp
