from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("envios/", views.shipment_list, name="shipment_list"),
    path("envios/nuevo/", views.shipment_create, name="shipment_create"),
    path("envios/<uuid:pk>/", views.shipment_detail, name="shipment_detail"),
    path("envios/<uuid:pk>/editar/", views.shipment_edit, name="shipment_edit"),
    path("envios/<uuid:pk>/asignar/", views.shipment_assign, name="shipment_assign"),
    path("envios/<uuid:pk>/estado/", views.shipment_status, name="shipment_status"),
    path("clientes/", views.customer_list, name="customer_list"),
    path("clientes/nuevo/", views.customer_form, name="customer_create"),
    path("clientes/<int:pk>/editar/", views.customer_form, name="customer_edit"),
]
