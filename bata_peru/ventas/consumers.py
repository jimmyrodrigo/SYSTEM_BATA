from channels.db import database_sync_to_async
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        self.destinatario_id = self.scope["url_route"]["kwargs"].get("destinatario_id")
        self.room_name = self.get_room_name(user.id, self.destinatario_id)

        if user.is_authenticated and self.destinatario_id:
            # Unirse al grupo del chat entre usuario y destinatario
            await self.channel_layer.group_add(self.room_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Descartar el grupo del WebSocket cuando se desconecta
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        # Recibir mensaje del WebSocket
        data = json.loads(text_data)
        mensaje = data.get("mensaje", "")
        imagen = data.get("imagen", None)
        user = self.scope["user"]
        destinatario_id = self.destinatario_id

        # Guardar el mensaje en la base de datos
        await self.save_message(user.id, destinatario_id, user.rol, mensaje, imagen)

        # Enviar el mensaje a ambos usuarios en el grupo
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "usuario": user.username,
                "rol": user.rol,
                "mensaje": mensaje,
                "imagen": imagen,
            }
        )

    async def chat_message(self, event):
        # Enviar el mensaje recibido al WebSocket del cliente
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, usuario_id, destinatario_id, rol, mensaje, imagen):
        # Importar modelos aquí para evitar problemas de carga temprana
        from .models import ChatMessage, UsuarioPersonalizado
        usuario = UsuarioPersonalizado.objects.get(id=usuario_id)
        destinatario = UsuarioPersonalizado.objects.get(id=destinatario_id)
        ChatMessage.objects.create(
            usuario=usuario,
            destinatario=destinatario,
            rol=rol,
            mensaje=mensaje,
            imagen=imagen
        )

    def get_room_name(self, user_id, destinatario_id):
        # Generar un nombre único para el grupo de chat
        ids = sorted([str(user_id), str(destinatario_id)])
        return f"chat_{ids[0]}_{ids[1]}"


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        print(f"[WS connect] user: {getattr(user, 'username', None)}, rol: {getattr(user, 'rol', None)}, authenticated: {user.is_authenticated}")

        if user.is_authenticated:
            # Unirse al grupo de notificaciones personal para cada usuario
            group_name = f"notificaciones_{user.username}"
            await self.channel_layer.group_add(group_name, self.channel_name)

            # Si es admin, también se une al grupo de admins
            if hasattr(user, 'rol') and user.rol == 'admin':
                print(f"[WS connect] ADMIN: {user.username} se une al grupo admin_notifications")
                await self.channel_layer.group_add("admin_notifications", self.channel_name)

            await self.accept()
        else:
            print("[WS connect] Usuario no autenticado, conexión rechazada")
            await self.close()

    async def disconnect(self, close_code):
        # Descartar el grupo de WebSocket cuando el usuario se desconecte
        user = self.scope["user"]
        if user.is_authenticated:
            group_name = f"notificaciones_{user.username}"
            await self.channel_layer.group_discard(group_name, self.channel_name)

            if hasattr(user, 'rol') and user.rol == 'admin':
                await self.channel_layer.group_discard("admin_notifications", self.channel_name)

    async def receive(self, text_data):
        # Aquí no procesamos mensajes de chat directamente para notificaciones
        pass

    async def send_notification(self, event):
        # Recibir el evento con el mensaje a enviar y reenviarlo tal cual al frontend
        message = event.get("message", {})
        print(f"[WS] send_notification: enviado a admin_notifications: {message}")
        await self.send(text_data=json.dumps(message))
