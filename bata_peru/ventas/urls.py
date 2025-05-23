from django.urls import path
from .views import (
    ventas_dashboard,
    historial_ventas,
    estadisticas_ventas,
    ver_comprobante,
    descargar_pdf,
    catalogo_productos,
    agregar_al_carrito,
    eliminar_del_carrito,
    realizar_compra,
    caja_usuario,
    consultar_dni,
    consultar_ruc,
    solicitar_anulacion_venta
)

urlpatterns = [
    path('dashboard/', ventas_dashboard, name='ventas_dashboard'),
    path('historial/', historial_ventas, name='historial_ventas'),
    path('caja/', caja_usuario, name='caja_usuario'),
    path('estadisticas/', estadisticas_ventas, name='estadisticas_ventas'),
    path('comprobante/<int:venta_id>/', ver_comprobante, name='ver_comprobante'),
    path('solicitar-anulacion/<int:venta_id>/', solicitar_anulacion_venta, name='solicitar_anulacion_venta'),
    path('descargar-pdf/<int:venta_id>/', descargar_pdf, name='descargar_pdf'),
    path('api/consultar-dni/', consultar_dni, name='consultar_dni'),
    path('api/consultar-ruc/', consultar_ruc, name='consultar_ruc'),
    path('catalogo/', catalogo_productos, name='catalogo_productos'),
    path('carrito/agregar/<int:producto_id>/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<int:producto_id>/', eliminar_del_carrito, name='eliminar_del_carrito'),
    path('realizar-compra/', realizar_compra, name='realizar_compra'),
]
