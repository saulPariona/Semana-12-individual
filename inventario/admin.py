import csv

from django.contrib import admin, messages
from django.db.models import Count, F, Sum
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Categoria, MensajeContacto, Producto


class ProductoInline(admin.TabularInline):
    model = Producto
    fields = ["sku", "nombre", "precio", "stock", "activo"]
    extra = 0
    show_change_link = True


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activa", "total_productos", "valor_total"]
    list_filter = ["activa"]
    search_fields = ["nombre"]
    inlines = [ProductoInline]

    def get_queryset(self, request):
        # Una sola query con agregaciones (evita N+1)
        return super().get_queryset(request).annotate(
            _total=Count("productos"), _valor=Sum(F("productos__precio") * F("productos__stock"))
        )

    @admin.display(description="N° productos", ordering="_total")
    def total_productos(self, obj):
        return obj._total

    @admin.display(description="Valor inventario (S/)", ordering="_valor")
    def valor_total(self, obj):
        return f"{obj._valor or 0:,.2f}"


class BajoStockFilter(admin.SimpleListFilter):
    title = "nivel de stock"
    parameter_name = "nivel"

    def lookups(self, request, model_admin):
        return [("bajo", "Bajo stock"), ("ok", "Stock suficiente"), ("agotado", "Agotado")]

    def queryset(self, request, queryset):
        if self.value() == "bajo":
            return queryset.filter(stock__lte=F("stock_minimo"))
        if self.value() == "ok":
            return queryset.filter(stock__gt=F("stock_minimo"))
        if self.value() == "agotado":
            return queryset.filter(stock=0)
        return queryset


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["sku", "nombre", "categoria", "precio", "stock", "estado_stock", "valor_inventario_display", "activo"]
    list_display_links = ["sku", "nombre"]
    list_editable = ["activo"]
    list_filter = ["activo", "categoria", BajoStockFilter, "creado"]
    search_fields = ["sku", "nombre", "categoria__nombre"]
    readonly_fields = ["creado_por", "creado", "actualizado", "valor_inventario_display"]
    list_select_related = ["categoria", "creado_por"]  # select_related() automático
    list_per_page = 20
    date_hierarchy = "creado"
    actions = ["activar", "desactivar", "reponer_stock", "exportar_csv"]
    fieldsets = [
        ("Identificación", {"fields": ["sku", "nombre", "categoria", "descripcion"]}),
        ("Precios y stock", {"fields": ["precio", "precio_oferta", "stock", "stock_minimo", "activo"]}),
        ("Auditoría", {"fields": ["creado_por", "creado", "actualizado", "valor_inventario_display"],
                       "classes": ["collapse"]}),
    ]

    @admin.display(description="Valor inventario (S/)")
    def valor_inventario_display(self, obj):
        return f"{obj.valor_inventario:,.2f}" if obj.pk else "-"

    @admin.display(description="Estado", ordering="stock")
    def estado_stock(self, obj):
        if obj.stock == 0:
            color, texto = "#c0392b", "AGOTADO"
        elif obj.bajo_stock:
            color, texto = "#e67e22", "BAJO"
        else:
            color, texto = "#27ae60", "OK"
        return format_html('<b style="color:{}">{}</b>', color, texto)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Activar productos seleccionados")
    def activar(self, request, queryset):
        n = queryset.update(activo=True)
        self.message_user(request, f"{n} producto(s) activados.", messages.SUCCESS)

    @admin.action(description="Desactivar productos seleccionados")
    def desactivar(self, request, queryset):
        n = queryset.update(activo=False)
        self.message_user(request, f"{n} producto(s) desactivados.", messages.WARNING)

    @admin.action(description="Reponer stock (+20 unidades)", permissions=["change"])
    def reponer_stock(self, request, queryset):
        n = queryset.update(stock=F("stock") + 20)
        self.message_user(request, f"Stock repuesto en {n} producto(s).", messages.SUCCESS)

    @admin.action(description="Exportar seleccionados a CSV")
    def exportar_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="productos.csv"'
        w = csv.writer(resp)
        w.writerow(["SKU", "Nombre", "Categoría", "Precio", "Stock", "Valor"])
        for p in queryset.select_related("categoria"):
            w.writerow([p.sku, p.nombre, p.categoria.nombre, p.precio, p.stock, p.valor_inventario])
        return resp


@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ["asunto", "nombre", "email", "recibido", "atendido"]
    list_filter = ["atendido", "recibido"]
    search_fields = ["asunto", "nombre", "email", "mensaje"]
    readonly_fields = ["nombre", "email", "asunto", "mensaje", "ip", "recibido"]
    actions = ["marcar_atendido"]

    def has_add_permission(self, request):
        return False  # los mensajes solo llegan desde el formulario público

    @admin.action(description="Marcar como atendido")
    def marcar_atendido(self, request, queryset):
        n = queryset.update(atendido=True)
        self.message_user(request, f"{n} mensaje(s) marcados como atendidos.")
