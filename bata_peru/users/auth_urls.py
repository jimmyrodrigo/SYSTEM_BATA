from django.urls import path
from .views import (
    login_view, consultar_dni, solicitudes_caja, aprobar_cierre_caja, gestion_usuarios,
    revisar_solicitudes_anulacion, aprobar_anulacion_venta, movimiento_caja,
    ventas_dashboard, catalogo_inventario, admin_dashboard, aprobar_apertura_caja, solicitudes_apertura_caja,
    solicitar_anulacion_venta
)
from .views_registro import registro
from django.contrib.auth.views import LogoutView
from .views import ventas_dashboard, catalogo_inventario, admin_dashboard, aprobar_apertura_caja, solicitudes_apertura_caja # Importa las vistas de los dashboards

urlpatterns = [
    # Rutas relacionadas con autenticación
    path('login/', login_view, name='login'),
    path('registro/', registro, name='registro'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'), 
    
    # Rutas para los dashboards según el rol
    path('ventas/dashboard/', ventas_dashboard, name='ventas_dashboard'),  # Ruta para el dashboard de ventas
    path('catalogo/inventario/', catalogo_inventario, name='catalogo_inventario'),  # Ruta para el catálogo de inventario
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    # Otras rutas
    path('caja/', movimiento_caja, name='movimiento_caja'),
    path('gestion-usuarios/', gestion_usuarios, name='gestion_usuarios'),
    path('api/consultar-dni/', consultar_dni, name='consultar_dni'),
    path('solicitudes-cierre/', solicitudes_caja, name='solicitudes_caja'),
    path('aprobar-cierre/<int:solicitud_id>/', aprobar_cierre_caja, name='aprobar_cierre_caja'),
    # Anulación de ventas
    path('revisar-solicitudes-anulacion/', revisar_solicitudes_anulacion, name='revisar_solicitudes_anulacion'),
    path('aprobar-anulacion/<int:solicitud_id>/', aprobar_anulacion_venta, name='aprobar_anulacion_venta'),
    path('solicitar-anulacion/<int:venta_id>/', solicitar_anulacion_venta, name='solicitar_anulacion_venta'),
    path('aprobar-apertura-caja/<int:solicitud_id>/', aprobar_apertura_caja, name='aprobar_apertura_caja'),
    path('solicitudes-apertura/', solicitudes_apertura_caja, name='solicitudes_apertura_caja'),
]
