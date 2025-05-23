from django.urls import path
from .views import login_view, registro_view, consultar_dni,solicitudes_cierre_caja, aprobar_cierre_caja, gestion_usuarios, revisar_solicitudes_anulacion,aprobar_anulacion_venta

from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', login_view, name='login'),
    path('registro/', registro_view, name='registro'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'), 
    path('gestion-usuarios/', gestion_usuarios, name='gestion_usuarios'),
    path('api/consultar-dni/', consultar_dni, name='consultar_dni'),
    path('solicitudes-cierre/', solicitudes_cierre_caja, name='solicitudes_cierre_caja'),
    path('aprobar-cierre/<int:caja_id>/', aprobar_cierre_caja, name='aprobar_cierre_caja'),
    path('revisar-solicitudes-anulacion/', revisar_solicitudes_anulacion, name='revisar_solicitudes_anulacion'),
path('aprobar-anulacion/<int:solicitud_id>/', aprobar_anulacion_venta, name='aprobar_anulacion_venta'),
]

