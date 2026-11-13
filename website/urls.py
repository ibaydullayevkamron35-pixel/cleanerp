from django.urls import path

from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('xizmatlar/', views.services_page, name='services_public'),
    path('kabinet/', views.cabinet, name='cabinet'),
    path('kabinet/buyurtmalar/', views.cabinet_orders, name='cabinet_orders'),
    path('kabinet/buyurtmalar/yangi/', views.cabinet_order_add, name='cabinet_order_add'),
    path('kabinet/buyurtmalar/<int:order_pk>/baholash/', views.cabinet_review, name='cabinet_review'),
    path('kabinet/obyektlar/', views.cabinet_facilities, name='cabinet_facilities'),
    path('kabinet/obyektlar/yangi/', views.cabinet_facility_add, name='cabinet_facility_add'),
    path('kabinet/hisob-fakturalar/', views.cabinet_invoices, name='cabinet_invoices'),
    path('kabinet/shikoyatlar/', views.cabinet_complaints, name='cabinet_complaints'),
]
