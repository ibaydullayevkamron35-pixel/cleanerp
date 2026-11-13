from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('', include('accounts.urls')),
    path('panel/', include('reports.urls')),
    path('panel/', include('crm.urls')),
    path('panel/', include('facilities.urls')),
    path('panel/', include('orders.urls')),
    path('panel/', include('hr.urls')),
    path('panel/', include('inventory.urls')),
    path('panel/', include('finance.urls')),
    path('panel/', include('quality.urls')),
    path('panel/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
