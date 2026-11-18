from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from inventario import views

admin.site.site_header = "Inventario S12 - Administración"
admin.site.site_title = "Inventario S12"
admin.site.index_title = "Panel de administración operativa"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("registro/", views.registro, name="registro"),
    path("", include("inventario.urls")),
]
