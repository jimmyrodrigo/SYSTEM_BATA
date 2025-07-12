from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def notificar_admin_solicitud(tipo, datos):
    print(f"[WS] Enviando a admin_notifications: tipo={tipo}, datos={datos}")
    """
    Envía una notificación WebSocket al grupo de administradores.
    tipo: 'nueva_apertura' o 'nueva_cierre' o 'respuesta_apertura' o 'respuesta_cierre'
    datos: dict con info relevante
    """
    channel_layer = get_channel_layer()
    # Enviar tanto 'tipo' como 'event' para máxima compatibilidad con el frontend
    # Añadir conteos actualizados si el evento es relevante
    from bata_peru.ventas.models import Caja, SolicitudAnulacionVenta
    payload = {
        'tipo': tipo,
        'event': tipo,  # Para que el frontend pueda usar ambos
        **datos
    }
    if tipo in ('nueva_cierre', 'respuesta_cierre'):
        payload['nuevas_cierre_count'] = Caja.objects.filter(cierre_solicitado=True, cierre_aprobado=False, esta_abierta=True).count()
    if tipo in ('nueva_anulacion', 'respuesta_anulacion'):
        payload['nuevas_anulacion_count'] = SolicitudAnulacionVenta.objects.filter(estado='pendiente').count()
    async_to_sync(channel_layer.group_send)(
        "admin_notifications",
        {
            'type': 'send_notification',
            'message': payload
        }
    )
