from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("contacto/", views.contacto, name="contacto"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("productos/", views.ProductoListView.as_view(), name="producto_list"),
    path("productos/nuevo/", views.producto_crear, name="producto_crear"),
    path("productos/<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="producto_editar"),
    path("reportes/", views.ReporteView.as_view(), name="reporte"),
]
