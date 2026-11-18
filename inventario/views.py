from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from .forms import ContactoForm, ProductoForm, RegistroForm
from .models import Categoria, Producto


def inicio(request):
    return render(request, "inventario/inicio.html")


def contacto(request):
    """Formulario clásico: nunca se usa request.POST directamente para guardar."""
    if request.method == "POST":
        form = ContactoForm(request.POST)
        if form.is_valid():
            form.guardar(ip=request.META.get("REMOTE_ADDR"))
            messages.success(request, "¡Mensaje enviado correctamente!")
            return redirect("inventario:contacto")  # patrón Post/Redirect/Get
    else:
        form = ContactoForm()
    return render(request, "inventario/contacto.html", {"form": form})


def registro(request):
    if request.user.is_authenticated:
        return redirect("inventario:dashboard")
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Bienvenido/a {user.first_name}, tu cuenta fue creada.")
            return redirect("inventario:dashboard")
    else:
        form = RegistroForm()
    return render(request, "registration/registro.html", {"form": form})


@login_required
def dashboard(request):
    ctx = {
        "total_productos": Producto.objects.count(),
        "bajo_stock": Producto.objects.filter(stock__lte=F("stock_minimo")).count(),
        "session_info": {
            "session_key": request.session.session_key,
            "expira_en_seg": request.session.get_expiry_age(),
            "ultima_actividad": request.session.get("ultima_actividad"),
            "paginas_vistas": request.session.get("paginas_vistas"),
            "historial": request.session.get("historial"),
        },
        "permisos": {
            "add_producto": request.user.has_perm("inventario.add_producto"),
            "change_producto": request.user.has_perm("inventario.change_producto"),
            "ver_reportes": request.user.has_perm("inventario.ver_reportes"),
        },
    }
    return render(request, "inventario/dashboard.html", ctx)


class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = "inventario/producto_list.html"
    context_object_name = "productos"
    paginate_by = 10

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q) | qs.filter(sku__icontains=q)
        return qs


@login_required
@permission_required("inventario.add_producto", raise_exception=True)
def producto_crear(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.creado_por = request.user
            producto.save()
            messages.success(request, f"Producto {producto.sku} creado.")
            return redirect("inventario:producto_list")
    else:
        form = ProductoForm()
    return render(request, "inventario/producto_form.html", {"form": form, "titulo": "Nuevo producto"})


class ProductoUpdateView(PermissionRequiredMixin, UpdateView):
    """PermissionRequiredMixin: si no está logueado -> LOGIN_URL; si no tiene permiso -> 403."""
    model = Producto
    form_class = ProductoForm
    template_name = "inventario/producto_form.html"
    permission_required = "inventario.change_producto"
    success_url = reverse_lazy("inventario:producto_list")
    extra_context = {"titulo": "Editar producto"}

    def form_valid(self, form):
        messages.success(self.request, "Producto actualizado.")
        return super().form_valid(form)


class ReporteView(PermissionRequiredMixin, ListView):
    template_name = "inventario/reporte.html"
    permission_required = "inventario.ver_reportes"
    context_object_name = "categorias"

    def get_queryset(self):
        return Categoria.objects.annotate(
            n=Count("productos"), unidades=Sum("productos__stock"),
            valor=Sum(F("productos__precio") * F("productos__stock")),
        )


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", {"reason": reason}, status=403)
