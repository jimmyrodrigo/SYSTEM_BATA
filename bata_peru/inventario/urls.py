from django.urls import path
from .views import (
    catalogo_inventario,
    control_stock_minimo, 
    agregar_producto,
    actualizar_stock,
    editar_producto,
    eliminar_producto,
)

urlpatterns = [
    path('catalogo/', catalogo_inventario, name='catalogo_inventario'),
    path('control-stock/', control_stock_minimo, name='control_stock_minimo'),
    path('editar/<int:producto_id>/', editar_producto, name='editar_producto'),
    path('eliminar/<int:producto_id>/', eliminar_producto, name='eliminar_producto'),
    path('actualizar-stock/<int:producto_id>/', actualizar_stock, name='actualizar_stock'),
    path('agregar/', agregar_producto, name='agregar_producto'),
]
