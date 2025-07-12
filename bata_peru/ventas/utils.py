from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def notificar_usuario(username, tipo):
    """
    Envía una notificación WebSocket al usuario con el username dado.
    tipo: 'aprobada' o 'rechazada'
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notificaciones_{username}",
        {
            'type': 'send_notification',
            'message': {
                'tipo': tipo
            }
        }
    )
