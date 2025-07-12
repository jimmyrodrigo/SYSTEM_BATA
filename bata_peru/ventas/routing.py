from django.urls import re_path
from . import consumers

# Definimos las rutas de WebSocket
websocket_urlpatterns = [
    # Ruta para las notificaciones de la caja (puedes añadir las notificaciones específicas que necesites aquí)
    re_path(r'ws/notificaciones_caja/$', consumers.NotificationConsumer.as_asgi()),

    # Ruta para las notificaciones administrativas (para admin)
    re_path(r'ws/admin_notifications/$', consumers.NotificationConsumer.as_asgi()),

    # Ruta para el chat entre usuarios (cajero y administrador) con destinatario específico
    re_path(r'ws/chat/(?P<destinatario_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
