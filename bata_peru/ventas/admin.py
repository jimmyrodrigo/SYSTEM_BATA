from django.contrib import admin
from .models import Venta, DetalleVenta

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombres_cliente', 'documento_cliente', 'tipo_comprobante', 'tipo_pago', 'fecha', 'vendedor', 'anulada')
    list_filter = ('tipo_comprobante', 'tipo_pago', 'anulada')
    search_fields = ('nombres_cliente', 'apellidos_cliente', 'documento_cliente')
    ordering = ('-fecha',)
    list_per_page = 25

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'producto', 'cantidad')
    search_fields = ('producto__nombre', 'venta__nombres_cliente')

from django.contrib import admin
from .models import Caja

@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_apertura', 'fecha_cierre', 'saldo_inicial', 'ingresos', 'egresos', 'saldo_final', 'esta_abierta')
    list_filter = ('usuario', 'esta_abierta', 'fecha_apertura')
    search_fields = ('usuario__username',)
