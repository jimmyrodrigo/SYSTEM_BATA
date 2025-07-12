
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template, render_to_string
from django.utils import timezone
from django.utils.timezone import now, localtime, make_aware
from django.db.models import Sum, F, Q
from datetime import datetime, timedelta
from html5lib import serialize
from .models import MovimientoCaja, SolicitudAnulacionVenta, SolicitudAperturaCaja, SolicitudCierreCaja, Venta, DetalleVenta, Caja
from bata_peru.ventas.models import DetalleVenta, Venta
from bata_peru.inventario.models import Categoria, Producto
from bata_peru.users.decorators import role_required
from xhtml2pdf import pisa
from django.core.serializers import serialize
from io import BytesIO
import os
from decimal import Decimal
from django.conf import settings
import requests
from django.contrib.auth.decorators import login_required
from bata_peru.ventas.admin_notifications import notificar_admin_solicitud
from django.views.decorators.csrf import csrf_exempt
import json
from channels.db import database_sync_to_async

def solicitar_apertura_caja(request):
    # ...lógica existente...
    # Obtener datos del request
    monto_inicial = float(request.POST.get('monto_inicial', 0))
    comentario = request.POST.get('comentario', '')
    # Crear la solicitud de apertura
    solicitud = SolicitudAperturaCaja.objects.create(
        usuario=request.user,
        monto_inicial=monto_inicial,
        comentario=comentario,
        fecha_solicitud=timezone.now(),
        estado='pendiente'
    )
    # Notificar a los administradores usando los campos correctos
    notificar_admin_solicitud('nueva_apertura', {
        'usuario': solicitud.usuario.username,
        'monto_inicial': str(solicitud.monto_inicial),
        'comentario': solicitud.comentario or '',
        'fecha': solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M')
    })
    # ...

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import ChatMessage, UsuarioPersonalizado


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

        # Si el usuario no es administrador, se envía el mensaje al administrador
        if user.rol != 'admin':
            # Enviar el mensaje al administrador para que lo vea y responda manualmente
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "chat_message",
                    "usuario": user.username,
                    "rol": user.rol,
                    "mensaje": mensaje,
                    "respuesta": "Esperando respuesta del administrador...",  # Mensaje que espera respuesta
                    "imagen": imagen,
                }
            )
        else:
            # El administrador solo ve los mensajes del usuario, puede responder manualmente
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "chat_message",
                    "usuario": user.username,
                    "rol": user.rol,
                    "mensaje": mensaje,
                    "respuesta": "",  # No hay respuesta automática
                    "imagen": imagen,
                }
            )

    async def chat_message(self, event):
        # Enviar el mensaje al WebSocket del cliente (usuario o administrador)
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, usuario_id, destinatario_id, rol, mensaje, imagen):
        # Guardar el mensaje en la base de datos
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

    # Método para que el administrador responda manualmente
    async def responder_como_admin(self, admin_user, respuesta):
        # Guardar la respuesta del administrador en la base de datos
        user = self.scope["user"]
        destinatario_id = self.destinatario_id
        await self.save_message(admin_user.id, destinatario_id, 'admin', respuesta, None)

        # Enviar la respuesta al cliente (cajero) para que vea la respuesta del administrador
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "usuario": admin_user.username,
                "rol": 'admin',
                "mensaje": respuesta,
                "respuesta": "",  # El administrador ha respondido manualmente
                "imagen": None,
            }
        )
def solicitar_cierre_caja(request):
    # ...lógica existente...
    # Obtener la caja abierta del usuario
    caja_abierta = Caja.objects.filter(usuario=request.user, esta_abierta=True).order_by('-fecha_apertura').first()
    comentario = request.POST.get('comentario', '')
    # Crear la solicitud de cierre
    solicitud = SolicitudCierreCaja.objects.create(
        usuario=request.user,
        caja=caja_abierta,
        comentario=comentario,
        estado='pendiente',
        fecha_solicitud=timezone.now()
    )
    # Notificar a los administradores usando los campos correctos
    notificar_admin_solicitud('nueva_cierre', {
        'usuario': solicitud.usuario.username,
        'comentario': solicitud.comentario or '',
        'fecha': solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M')
    })

@csrf_exempt
def chatbot(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mensaje = data.get('mensaje', '')
        except Exception:
            mensaje = ''
        # Aquí va la lógica de respuesta del bot
        if mensaje.strip() == '':
            respuesta = 'Por favor, escribe un mensaje.'
        elif 'hola' in mensaje.lower():
            respuesta = '¡Hola! ¿En qué puedo ayudarte hoy?'
        elif 'precio' in mensaje.lower():
            respuesta = '¿Sobre qué producto deseas saber el precio?'
        else:
            respuesta = 'Soy el asistente virtual. ¿Cómo puedo ayudarte?'
        return JsonResponse({'respuesta': respuesta})
    return JsonResponse({'respuesta': 'Método no permitido.'}, status=405)

def carrito(request):
    carrito_sesion = request.session.get('carrito', {})
    carrito_items = []
    subtotal = Decimal('0.00')  # precio sin IGV

    for producto_id, cantidad in carrito_sesion.items():
        producto = get_object_or_404(Producto, id=producto_id)
        precio_unitario = producto.precio  # ya sin IGV
        total_item = precio_unitario * cantidad
        subtotal += total_item
        carrito_items.append({
            'producto': producto,
            'cantidad': cantidad,
            'precio_unitario': precio_unitario,
            'total': total_item,
        })

    igv = subtotal * Decimal('0.18')
    total_con_igv = subtotal + igv

    context = {
        'carrito_items': carrito_items,
        'subtotal': subtotal,          # base imponible
        'igv': igv,                    # IGV estimado
        'total': total_con_igv,        # total con IGV incluido
    }
    return render(request, 'ventas/carrito.html', context)

@login_required
def caja_usuario(request):
    usuario = request.user

    caja_abierta = Caja.objects.filter(usuario=usuario, esta_abierta=True).order_by('-fecha_apertura').first()
    # Si hay una solicitud aprobada pero NO hay caja abierta, limpiar esa solicitud para evitar limbo
    solicitud_aprobada = SolicitudAperturaCaja.objects.filter(usuario=usuario, estado='aprobada').first()
    if solicitud_aprobada and not caja_abierta:
        solicitud_aprobada.delete()
    # Solo mostrar la pendiente
    solicitud_apertura = SolicitudAperturaCaja.objects.filter(usuario=usuario, estado='pendiente').first()

    if request.method == 'POST':
        accion = request.POST.get('accion')


        if accion == 'solicitar_apertura':
            if solicitud_apertura:
                return JsonResponse({
                    'status': 'error',
                    'message': "Ya tienes una solicitud de apertura pendiente."
                })

            monto_inicial = float(request.POST.get('monto_inicial', 0))
            comentario = request.POST.get('comentario', '')

            if monto_inicial < 0:
                return JsonResponse({
                    'status': 'error',
                    'message': "Monto inicial inválido"
                })

            solicitud = SolicitudAperturaCaja.objects.create(
                usuario=usuario,
                monto_inicial=monto_inicial,
                comentario=comentario,
                fecha_solicitud=timezone.now(),
                estado='pendiente'
            )

            # Notificar a los administradores en tiempo real
            notificar_admin_solicitud('nueva_apertura', {
                'usuario': solicitud.usuario.username,
                'monto_inicial': str(solicitud.monto_inicial),
                'comentario': solicitud.comentario or '',
                'fecha': solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M')
            })

            return JsonResponse({
                'status': 'success',
                'message': "Solicitud de apertura enviada correctamente.",
                'solicitud_apertura': {
                    'usuario': solicitud.usuario.username,
                    'fecha_solicitud': solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M'),
                    'monto_inicial': str(solicitud.monto_inicial),
                    'comentario': solicitud.comentario or ''
                }
            })


        elif accion == 'solicitar_cierre':
            if not caja_abierta:
                return JsonResponse({
                    'status': 'error',
                    'message': "No tienes una caja abierta para cerrar."
                })

            if SolicitudCierreCaja.objects.filter(usuario=usuario, caja=caja_abierta, estado='pendiente').exists():
                return JsonResponse({
                    'status': 'error',
                    'message': "Ya existe una solicitud de cierre pendiente."
                })

            comentario = request.POST.get('comentario', '')

            solicitud_cierre = SolicitudCierreCaja.objects.create(
                usuario=usuario,
                caja=caja_abierta,
                comentario=comentario,
                estado='pendiente',
                fecha_solicitud=timezone.now()
            )

            # Notificar a los administradores en tiempo real
            notificar_admin_solicitud('nueva_cierre', {
                'usuario': solicitud_cierre.usuario.username,
                'comentario': solicitud_cierre.comentario or '',
                'fecha': solicitud_cierre.fecha_solicitud.strftime('%d/%m/%Y %H:%M')
            })

            return JsonResponse({
                'status': 'success',
                'message': "Solicitud de cierre enviada correctamente.",
                'solicitud_cierre': {
                    'usuario': solicitud_cierre.usuario.username,
                    'fecha_solicitud': solicitud_cierre.fecha_solicitud.strftime('%d/%m/%Y %H:%M'),
                    'comentario': solicitud_cierre.comentario or ''
                }
            })

    return render(request, 'ventas/caja_usuario.html', {
        'caja_abierta': caja_abierta,
        'solicitud_apertura': solicitud_apertura
    })

@login_required
@login_required
def estado_solicitud_caja(request):
    usuario = request.user
    solicitud = SolicitudAperturaCaja.objects.filter(usuario=usuario).order_by('-fecha_solicitud').first()
    caja_abierta = Caja.objects.filter(usuario=usuario, esta_abierta=True).exists()

    if caja_abierta:
        # Si hay caja abierta, la solicitud ya fue aprobada y la caja está disponible
        estado = 'aprobada'
    elif solicitud:
        # Si no hay caja abierta, pero hay solicitud
        if solicitud.estado == 'aprobada':
            # Si la solicitud está aprobada pero no hay caja, forzar a que el usuario vuelva a solicitar
            estado = 'ninguna'
        else:
            estado = solicitud.estado
    else:
        estado = 'ninguna'

    return JsonResponse({
        'estado': estado  # puede ser 'pendiente', 'aprobada', 'rechazada', 'ninguna'
    })


def consultar_dni(request):
    dni = request.GET.get('dni')
    if not dni:
        return JsonResponse({'error': 'DNI requerido'}, status=400)

    try:
        headers = {'Authorization': 'Bearer apis-token-16472.iRBbmPL2BcwxdpOiU5er7wOizKerRd19'}
        response = requests.get(f'https://api.apis.net.pe/v2/reniec/dni?numero={dni}', headers=headers)
        return JsonResponse(response.json())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def consultar_ruc(request):
    ruc = request.GET.get('ruc')
    if not ruc:
        return JsonResponse({'error': 'RUC requerido'}, status=400)

    try:
        headers = {
            'Authorization': 'Bearer apis-token-16805.KFKKQEzb4ANkMF1zqz6C1NQuHQIhcyi1'
        }
        response = requests.get(f'https://api.apis.net.pe/v2/sunat/ruc/full?numero={ruc}', headers=headers)
        data = response.json()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@role_required('empleado')
def ventas_dashboard(request):
    return redirect('catalogo_productos')


def obtener_productos_api(request):
    """
    Vista para obtener productos en formato JSON.
    Los productos se pueden filtrar por los parámetros de la solicitud GET.
    """
    # Obtener productos
    productos = Producto.objects.all()

    # Obtener categorías y otros filtros
    categorias = Categoria.objects.values_list('nombre', flat=True).distinct()
    tallas = productos.values_list('talla', flat=True).distinct().exclude(talla__isnull=True).exclude(talla__exact='')
    marcas = productos.values_list('marca', flat=True).distinct()
    colores = productos.values_list('color', flat=True).distinct()

    # Aplicar filtros si se proporcionan en la solicitud GET
    categoria = request.GET.get('categoria')
    if categoria:
        productos = productos.filter(categoria__nombre=categoria)

    talla = request.GET.get('talla')
    if talla:
        productos = productos.filter(talla=talla)

    marca = request.GET.get('marca')
    if marca:
        productos = productos.filter(marca=marca)

    color = request.GET.get('color')
    if color:
        productos = productos.filter(color=color)

    # Preparamos los datos en formato JSON
    data = {
        'productos': list(productos.values('id', 'nombre', 'marca', 'talla', 'color', 'precio', 'categoria__nombre')),
        'categorias': list(categorias),
        'tallas': list(tallas),
        'marcas': list(marcas),
        'colores': list(colores)
    }

    # Retornar la respuesta JSON
    return JsonResponse(data)



@login_required
@role_required('empleado')
def catalogo_productos(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.values_list('nombre', flat=True).distinct()

    # Obtener listas únicas para filtros
    tallas = productos.values_list('talla', flat=True).distinct().exclude(talla__isnull=True).exclude(talla__exact='')
    marcas = productos.values_list('marca', flat=True).distinct()
    colores = productos.values_list('color', flat=True).distinct()

    # Aplicar filtros desde GET
    categoria = request.GET.get('categoria')
    if categoria:
        productos = productos.filter(categoria__nombre=categoria)

    talla = request.GET.get('talla')
    if talla:
        productos = productos.filter(talla=talla)

    marca = request.GET.get('marca')
    if marca:
        productos = productos.filter(marca=marca)

    color = request.GET.get('color')
    if color:
        productos = productos.filter(color=color)

    # Ahora usa render() para devolver la respuesta con el contexto
    context = {
        'productos': productos,
        'categorias': categorias,
        'tallas': tallas,
        'marcas': marcas,
        'colores': colores,
    }
    return render(request, 'ventas/catalogo_productos.html', context) 

from django.http import JsonResponse
@login_required
@role_required('empleado')
def modificar_cantidad_carrito(request, producto_id):
    if request.method == 'POST':
        accion = request.POST.get('accion')
        carrito = request.session.get('carrito', {})

        producto = get_object_or_404(Producto, id=producto_id)
        producto_id_str = str(producto_id)

        cantidad_actual = carrito.get(producto_id_str, 0)

        if accion == 'mas':
            # Incrementar cantidad, sin pasar stock disponible
            if cantidad_actual < producto.cantidad:
                carrito[producto_id_str] = cantidad_actual + 1
            else:
                messages.error(request, "No hay más stock disponible para este producto.")
        elif accion == 'menos':
            # Decrementar cantidad, mínimo 1
            if cantidad_actual > 1:
                carrito[producto_id_str] = cantidad_actual - 1
            else:
                # Si quieres eliminar el producto cuando es 1 y le dan menos, se puede hacer aquí:
                # carrito.pop(producto_id_str)
                messages.error(request, "La cantidad mínima es 1.")
        else:
            messages.error(request, "Acción inválida.")

        # Guardar cambios en sesión
        request.session['carrito'] = carrito

    return redirect('carrito')

@login_required
@role_required('empleado')
def agregar_al_carrito(request, producto_id):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id=producto_id)
        cantidad = int(request.POST.get('cantidad', 1))

        carrito = request.session.get('carrito', {})
        carrito[str(producto_id)] = carrito.get(str(producto_id), 0) + cantidad

        request.session['carrito'] = carrito
        messages.success(request, f"{producto.nombre} agregado al carrito.")

        total_cantidad = sum(carrito.values())  # Total real del carrito
        return JsonResponse({'success': True, 'total_cantidad': total_cantidad})

    return redirect('catalogo_productos')



@role_required('empleado')
def eliminar_del_carrito(request, producto_id):
    if request.method == 'POST':
        carrito = request.session.get('carrito', {})
        producto_id = str(producto_id)
        if producto_id in carrito:
            del carrito[producto_id]
            request.session['carrito'] = carrito
            messages.success(request, "Producto eliminado del carrito.")
    return redirect('carrito')

@login_required
@role_required('empleado')
def realizar_compra(request):
    carrito = request.session.get('carrito', {})

    if not carrito:
        messages.info(request, "El carrito está vacío.")
        return redirect('catalogo_productos')

    productos = []
    total_final = Decimal('0.00')

    tipo_comprobante = request.POST.get('tipo_comprobante') if request.method == 'POST' else 'boleta'

    for producto_id, cantidad in carrito.items():
        producto = get_object_or_404(Producto, id=producto_id)

        precio_unitario_real = producto.precio  # ya es precio sin IGV
        subtotal = precio_unitario_real * cantidad
        total_final += subtotal

        productos.append({
            'producto': producto,
            'cantidad': cantidad,
            'subtotal': subtotal,
            'precio_unitario_real': precio_unitario_real,
        })

    if tipo_comprobante == 'factura':
        igv = total_final * Decimal('0.18')
    else:
        igv = Decimal('0.00')

    total_a_pagar = total_final + igv

    if request.method == 'POST':
        tipo_pago = request.POST.get('tipo_pago')
        tipo_documento = request.POST.get('tipo_documento')
        documento = request.POST.get('documento_cliente')
        monto_pagado = Decimal(request.POST.get('monto_pagado', '0'))

        if tipo_pago == 'efectivo' and monto_pagado < total_a_pagar:
            messages.error(request, "El monto pagado no cubre el total.")
            return redirect('realizar_compra')

        if tipo_comprobante == 'factura':
            razon_social = request.POST.get('razon_social', '').strip()
            nombres = ''
            apellidos = ''
        else:
            nombres = request.POST.get('nombres_cliente', '').strip()
            apellidos = request.POST.get('apellidos_cliente', '').strip()
            razon_social = ''

        caja = Caja.objects.filter(usuario=request.user, esta_abierta=True).last()
        if not caja:
            messages.error(request, "No hay una caja abierta actualmente.")
            return redirect('realizar_compra')

        if tipo_pago == 'efectivo':
            vuelto = monto_pagado - total_a_pagar
            if vuelto > caja.saldo_final:
                messages.error(request, f"No se puede completar la venta. El vuelto ({vuelto:.2f}) excede el saldo disponible en caja.")
                return redirect('realizar_compra')
        else:
            vuelto = Decimal('0.00')
            monto_pagado = total_a_pagar

        venta = Venta.objects.create(
            vendedor=request.user,
            nombres_cliente=nombres,
            razon_social=razon_social,
            apellidos_cliente=apellidos,
            documento_cliente=documento,
            tipo_documento=tipo_documento,
            tipo_comprobante=tipo_comprobante,
            tipo_pago=tipo_pago,
            monto_pagado=monto_pagado,
            vuelto=vuelto,
            total=total_a_pagar,
            fecha=timezone.now()
        )

        for item in productos:
            producto = item['producto']
            cantidad = item['cantidad']
            if producto.cantidad < cantidad:
                messages.error(request, f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.cantidad}")
                venta.delete()
                return redirect('realizar_compra')

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad
            )
            producto.cantidad -= cantidad
            producto.save()

        caja.ingresos += total_a_pagar
        caja.egresos += vuelto
        caja.saldo_final = caja.saldo_inicial + caja.ingresos
        caja.save()
        
        movimiento = MovimientoCaja.objects.create(
            caja=caja,
            tipo='venta',
            descripcion=f"Venta ID {venta.id}",
            nombre_cliente=f"{venta.nombres_cliente} {venta.apellidos_cliente or ''}".strip(),
            nombre_empresa=venta.razon_social or '',
            PagoCliente=venta.monto_pagado,
            VueltoCliente=venta.vuelto,
            monto=venta.total,
        )
        # Notificar a los administradores por WebSocket sobre el nuevo movimiento
        from bata_peru.ventas.admin_notifications import notificar_admin_solicitud
        notificar_admin_solicitud('nuevo_movimiento', {
            'tipo': 'movimiento',
            'accion': 'creado',
            'usuario': request.user.username,
            'monto': str(venta.total),
            'descripcion': movimiento.descripcion,
            'fecha': str(movimiento.fecha) if hasattr(movimiento, 'fecha') else str(timezone.now()),
        })

        if 'carrito' in request.session:
            del request.session['carrito']

        messages.success(request, f"Venta registrada correctamente. Vuelto: S/ {vuelto:.2f}")
        return redirect('ver_comprobante', venta_id=venta.id)

    return render(request, 'ventas/realizar_compra.html', {
        'productos': productos,
        'igv': igv,
        'total_final': total_a_pagar,
        'total': total_final,
        'tipo_comprobante': tipo_comprobante,
    })

@role_required('empleado')
@login_required
def ver_comprobante(request, venta_id):
    from django.utils.timezone import localtime
    from django.utils.dateformat import DateFormat

    venta = get_object_or_404(Venta, id=venta_id)
    detalles = venta.detalleventa_set.all()

    detalles_enriquecidos = []
    base = Decimal('0.00')

    for detalle in detalles:
        precio_unitario = detalle.producto.precio  # ya es base sin IGV
        subtotal = precio_unitario * detalle.cantidad
        base += subtotal

        detalles_enriquecidos.append({
            'producto': detalle.producto.nombre,
            'cantidad': detalle.cantidad,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal
        })

    igv = base * Decimal('0.18') if venta.tipo_comprobante == 'factura' else Decimal('0.00')
    total = base + igv
    fecha = DateFormat(localtime(venta.fecha)).format('d/m/Y H:i')
    razon_social = venta.razon_social if venta.tipo_comprobante == 'factura' else ''
    logo_abspath = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'logo_bata.png')
    logo_path = f"file:///{logo_abspath.replace('\\', '/')}"
    ruc_empresa = "20123456789"  # Cambia por el RUC real si lo tienes en settings
    slogan = "Calzado que te acompaña siempre."

    html = f"""
    <html>
    <head>
    <meta charset='utf-8'>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; margin: 0; background: #fff; }}
        .comprobante-container {{ max-width: 520px; margin: 18px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 18px 22px; }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
        .logo {{ width: 90px; margin-left: 12px; margin-top: 2px; }}
        .titulo {{ font-size: 18px; font-weight: bold; color: #d90429; margin-bottom: 6px; letter-spacing: 1px; text-align: left; }}
        .ruc {{ font-size: 12px; color: #23252B; text-align: left; margin-bottom: 2px; }}
        .slogan {{ font-size: 10px; color: #d90429; text-align: left; margin-bottom: 8px; }}
        .datos {{ font-size: 13px; margin-bottom: 10px; color: #23252B; }}
        .datos strong {{ display: inline-block; width: 120px; color: #d90429; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 10px; }}
        th {{ background: #d90429; color: #fff; font-weight: 600; border: none; padding: 7px 4px; border-radius: 4px 4px 0 0; }}
        td {{ background: #f9f9f9; border: none; padding: 6px 4px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        tr:last-child td {{ border-bottom: none; }}
        .totales {{ margin-top: 10px; text-align: right; font-size: 13px; color: #23252B; }}
        .totales strong {{ color: #d90429; }}
        .footer {{ text-align: center; font-size: 10px; color: #888; margin-top: 12px; }}
    </style>
    </head>
    <body>
      <div class='comprobante-container'>
        <div class='header'>
          <div>
            <div class='titulo'>COMPROBANTE DE {venta.tipo_comprobante.upper()}</div>
            <div class='ruc'>RUC: {ruc_empresa}</div>
            <div class='slogan'>{slogan}</div>
          </div>
          <img src='{logo_path}' class='logo' />
        </div>
        <div class='datos'>
            <p><strong>Fecha:</strong> {fecha}</p>
            <p><strong>Tipo Documento:</strong> {venta.get_tipo_documento_display()} &nbsp;&nbsp;
               <strong>Número:</strong> {venta.documento_cliente}</p>"""
    if venta.tipo_comprobante == 'boleta':
        html += f"<p><strong>Cliente:</strong> {venta.nombres_cliente} {venta.apellidos_cliente or ''}</p>"
    else:
        html += f"<p><strong>Razón Social:</strong> {razon_social}</p>"
    html += """
        </div>
        <table>
            <thead>
                <tr>
                    <th>Producto</th>
                    <th>Cant.</th>
                    <th>Precio Unitario</th>
                    <th>Subtotal</th>
                </tr>
            </thead>
            <tbody>"""
    for item in detalles_enriquecidos:
        html += f"""
        <tr>
            <td>{item['producto']}</td>
            <td>{item['cantidad']}</td>
            <td>S/ {item['precio_unitario']:.2f}</td>
            <td>S/ {item['subtotal']:.2f}</td>
        </tr>"""
    html += f"""
            </tbody>
        </table>
        <div class='totales'>
            <p><strong>Base Imponible:</strong> S/ {base:.2f}</p>
            <p><strong>IGV:</strong> S/ {igv:.2f}</p>
            <p><strong>Total:</strong> <strong>S/ {total:.2f}</strong></p>
            <p><strong>Pagó:</strong> S/ {venta.monto_pagado:.2f} &nbsp;&nbsp;
               <strong>Vuelto:</strong> S/ {venta.vuelto:.2f}</p>
        </div>
        <div class='footer'>Documento generado por Bata Perú &copy; {datetime.now().year}</div>
      </div>
    </body>
    </html>
    """

    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)
    if pisa_status.err:
        return HttpResponse("Error al generar comprobante", status=500)

    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprobante_{venta.id}.pdf"'
    return response


@role_required('empleado')
def descargar_pdf(request, venta_id):
    from django.utils.dateformat import DateFormat
    from django.utils.timezone import localtime

    venta = get_object_or_404(Venta, id=venta_id, vendedor=request.user)
    detalles = venta.detalleventa_set.all()

    detalles_enriquecidos = []
    base = Decimal('0.00')

    for detalle in detalles:
        precio_unitario = detalle.producto.precio  # ya es base sin IGV
        subtotal = precio_unitario * detalle.cantidad
        base += subtotal
        detalles_enriquecidos.append({
            'producto': detalle.producto.nombre,
            'cantidad': detalle.cantidad,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal
        })

    igv = base * Decimal('0.18') if venta.tipo_comprobante == 'factura' else Decimal('0.00')
    total = base + igv
    fecha = DateFormat(localtime(venta.fecha)).format('d/m/Y H:i')
    logo_abspath = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'logo_bata.png')
    logo_path = f"file:///{logo_abspath.replace('\\', '/')}"
    ruc_empresa = "20123456789"  # Cambia por el RUC real si lo tienes en settings
    slogan = "Calzado que te acompaña siempre."

    html = f"""
    <html>
    <head>
    <meta charset='utf-8'>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; margin: 0; background: #fff; }}
        .comprobante-container {{ max-width: 520px; margin: 18px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 18px 22px; }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
        .logo {{ width: 90px; margin-left: 12px; margin-top: 2px; }}
        .titulo {{ font-size: 18px; font-weight: bold; color: #d90429; margin-bottom: 6px; letter-spacing: 1px; text-align: left; }}
        .ruc {{ font-size: 12px; color: #23252B; text-align: left; margin-bottom: 2px; }}
        .slogan {{ font-size: 10px; color: #d90429; text-align: left; margin-bottom: 8px; }}
        .datos {{ font-size: 13px; margin-bottom: 10px; color: #23252B; }}
        .datos strong {{ display: inline-block; width: 120px; color: #d90429; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 10px; }}
        th {{ background: #d90429; color: #fff; font-weight: 600; border: none; padding: 7px 4px; border-radius: 4px 4px 0 0; }}
        td {{ background: #f9f9f9; border: none; padding: 6px 4px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        tr:last-child td {{ border-bottom: none; }}
        .totales {{ margin-top: 10px; text-align: right; font-size: 13px; color: #23252B; }}
        .totales strong {{ color: #d90429; }}
        .footer {{ text-align: center; font-size: 10px; color: #888; margin-top: 12px; }}
    </style>
    </head>
    <body>
      <div class='comprobante-container'>
        <div class='header'>
          <div>
            <div class='titulo'>COMPROBANTE DE {venta.tipo_comprobante.upper()}</div>
            <div class='ruc'>RUC: {ruc_empresa}</div>
            <div class='slogan'>{slogan}</div>
          </div>
          <img src='{logo_path}' class='logo' />
        </div>
        <div class='datos'>
            <p><strong>Fecha:</strong> {fecha}</p>
            <p><strong>Tipo Documento:</strong> {venta.get_tipo_documento_display()} &nbsp;&nbsp;
               <strong>Documento:</strong> {venta.documento_cliente}</p>"""
    if venta.tipo_comprobante == 'boleta':
        html += f"<p><strong>Cliente:</strong> {venta.nombres_cliente} {venta.apellidos_cliente or ''}</p>"
    else:
        html += f"<p><strong>Razón Social:</strong> {venta.razon_social}</p>"
    html += """
        </div>
        <table>
            <thead>
                <tr>
                    <th>Producto</th>
                    <th>Cant.</th>
                    <th>Precio Unitario</th>
                    <th>Subtotal</th>
                </tr>
            </thead>
            <tbody>"""
    for item in detalles_enriquecidos:
        html += f"""
        <tr>
            <td>{item['producto']}</td>
            <td>{item['cantidad']}</td>
            <td>S/ {item['precio_unitario']:.2f}</td>
            <td>S/ {item['subtotal']:.2f}</td>
        </tr>"""
    html += f"""
            </tbody>
        </table>
        <div class='totales'>
            <p><strong>Base Imponible:</strong> S/ {base:.2f}</p>
            <p><strong>IGV:</strong> S/ {igv:.2f}</p>
            <p><strong>Total a Pagar:</strong> <strong>S/ {total:.2f}</strong></p>
            <p style='margin-top:10px;'><strong>Pagó:</strong> S/ {venta.monto_pagado:.2f} &nbsp;&nbsp;
               <strong>Vuelto:</strong> S/ {venta.vuelto:.2f}</p>
        </div>
        <div class='footer'>Documento generado por Bata Perú &copy; {datetime.now().year}</div>
      </div>
    </body>
    </html>
    """

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=comprobante_{venta.id}.pdf'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)

    return response




from django.shortcuts import render
from django.http import HttpResponse
from django.template.defaultfilters import date as django_date
from django.utils.timezone import make_aware
from django.utils import timezone
from django.core.serializers import serialize
from io import BytesIO
from datetime import datetime
from bata_peru.ventas.models import Venta
from xhtml2pdf import pisa
from django.contrib.auth.decorators import login_required

@login_required
def historial_ventas(request):
    ventas = Venta.objects.all()
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    tipo_pago = request.GET.get('tipo_pago')
    tipo_documento = request.GET.get('tipo_documento')
    documento_cliente = request.GET.get('documento_cliente')
    producto_id = request.GET.get('producto_id')  # Filtro para producto
    cantidad_minima = request.GET.get('cantidad_minima')  # Filtro para cantidad mínima

    if fecha_inicio:
        try:
            inicio = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            ventas = ventas.filter(fecha__gte=inicio)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fin = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d'))
            ventas = ventas.filter(fecha__lt=fin + timezone.timedelta(days=1))
        except ValueError:
            pass

    if estado == 'activa':
        ventas = ventas.filter(anulada=False)
    elif estado == 'anulada':
        ventas = ventas.filter(anulada=True)
    if tipo_pago:
        ventas = ventas.filter(tipo_pago=tipo_pago)
    if tipo_documento:
        ventas = ventas.filter(tipo_documento=tipo_documento)
    if documento_cliente:
        ventas = ventas.filter(documento_cliente__icontains=documento_cliente)

    if producto_id:
        # Filtrar las ventas que contienen el producto en el detalle de venta
        ventas = ventas.filter(detalleventa__producto__id=producto_id)
    
    if cantidad_minima:
        # Filtrar ventas donde la cantidad mínima de productos se cumple
        ventas = ventas.filter(detalleventa__cantidad__gte=cantidad_minima)

    ventas = ventas.order_by('-fecha')

    export = request.GET.get('export')

    if export == 'pdf':
        logo_path = f"file://{os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'logo_bata.png')}"
        ruc_empresa = "20123456789"  # Cambia por el RUC real si lo tienes en settings
        slogan = "Calzado que te acompaña siempre."
        html = f"""
        <html>
        <head>
        <meta charset='utf-8'>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; margin: 0; background: #fff; }}
            .comprobante-container {{ max-width: 700px; margin: 18px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 18px 22px; }}
            .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }}
            .logo {{ width: 90px; margin-left: 12px; margin-top: 2px; }}
            .titulo {{ font-size: 18px; font-weight: bold; color: #d90429; margin-bottom: 6px; letter-spacing: 1px; text-align: left; }}
            .ruc {{ font-size: 12px; color: #23252B; text-align: left; margin-bottom: 2px; }}
            .slogan {{ font-size: 10px; color: #d90429; text-align: left; margin-bottom: 8px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 10px; }}
            th {{ background: #d90429; color: #fff; font-weight: 600; border: none; padding: 7px 4px; border-radius: 4px 4px 0 0; }}
            td {{ background: #f9f9f9; border: none; padding: 6px 4px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
            tr:last-child td {{ border-bottom: none; }}
            .footer {{ text-align: center; font-size: 10px; color: #888; margin-top: 12px; }}
        </style>
        </head>
        <body>
        <div class='comprobante-container'>
          <div class='header'>
            <div>
              <div class='titulo'>📄 Historial de Ventas</div>
              <div class='ruc'>RUC: {ruc_empresa}</div>
              <div class='slogan'>{slogan}</div>
            </div>
            <img src='{logo_path}' class='logo' />
          </div>
          <table>
            <thead>
                <tr>
                    <th>Cliente</th>
                    <th>Documento</th>
                    <th>Fecha</th>
                    <th>Total</th>
                    <th>Pago</th>
                    <th>Vuelto</th>
                    <th>Estado</th>
                    <th>Cantidad Productos</th>
                </tr>
            </thead>
            <tbody>"""
        for v in ventas:
            estado_txt = "Anulada" if v.anulada else "Activa"
            cliente_nombre = v.razon_social if v.tipo_comprobante == 'factura' else f"{v.nombres_cliente} {v.apellidos_cliente or ''}"
            cantidad_productos = sum(detalle.cantidad for detalle in v.detalleventa_set.all())
            html += f"""
                    <tr>
                        <td>{cliente_nombre}</td>
                        <td>{v.tipo_documento.upper()} {v.documento_cliente}</td>
                        <td>{django_date(v.fecha, 'Y-m-d H:i')}</td>
                        <td>S/ {v.total:.2f}</td>
                        <td>{v.get_tipo_pago_display()}</td>
                        <td>S/ {v.vuelto:.2f}</td>
                        <td>{estado_txt}</td>
                        <td>{cantidad_productos}</td>
                    </tr>"""
        html += f"""
                </tbody>
            </table>
            <div class='footer'>Documento generado por Bata Perú &copy; {datetime.now().year} &mdash; Exportado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
        </div>
        </body>
        </html>
        """
        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)
        if pisa_status.err:
            return HttpResponse("Error generando PDF", status=500)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="ventas.pdf"'
        return response

    elif export == 'xml':
        xml_data = serialize('xml', ventas)
        response = HttpResponse(xml_data, content_type='application/xml')
        response['Content-Disposition'] = 'attachment; filename="ventas.xml"'
        return response

    return render(request, 'ventas/historial_ventas.html', {
        'ventas': ventas,
        'venta': Venta
    })


#Solicitar anular venta
@role_required('empleado')
def solicitar_anulacion_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, vendedor=request.user)

    if venta.anulada:
        messages.warning(request, "La venta ya está anulada.")
        return redirect('historial_ventas')

    if request.method == 'POST':
        comentario = request.POST.get('comentario', '').strip()
        if not comentario:
            messages.error(request, "Debe ingresar un comentario para la solicitud de anulación.")
            return redirect('solicitar_anulacion_venta', venta_id=venta.id)

        # Verificar si ya existe una solicitud pendiente
        existe_solicitud = SolicitudAnulacionVenta.objects.filter(venta=venta, estado='pendiente').exists()
        if existe_solicitud:
            messages.info(request, "Ya tienes una solicitud de anulación pendiente para esta venta.")
            return redirect('historial_ventas')

        SolicitudAnulacionVenta.objects.create(
            venta=venta,
            usuario_solicitante=request.user,
            comentario=comentario
        )
        # Notificar a los administradores por WebSocket
        from bata_peru.ventas.admin_notifications import notificar_admin_solicitud
        notificar_admin_solicitud('nueva_anulacion', {
            'usuario': request.user.username,
            'venta_id': venta.id,
            'monto': str(venta.total),
            'comentario': comentario,
            'fecha': timezone.now().strftime('%d/%m/%Y %H:%M')
        })
        messages.success(request, "Solicitud de anulación enviada y notificación enviada al administrador.")
        return redirect('historial_ventas')

    return render(request, 'ventas/solicitar_anulacion.html', {'venta': venta})

# Anular venta



#from django.shortcuts import render
from django.utils.timezone import make_aware
from datetime import datetime
from bata_peru.ventas.models import Venta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from bata_peru.users.decorators import role_required
from django.template.defaultfilters import date as django_date

@role_required('empleado')
@login_required
def historial_ventas(request):
    ventas = Venta.objects.filter(vendedor=request.user)

    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    tipo_pago = request.GET.get('tipo_pago')
    tipo_documento = request.GET.get('tipo_documento')
    documento_cliente = request.GET.get('documento_cliente')
    producto_id = request.GET.get('producto_id')
    talla = request.GET.get('talla')
    color = request.GET.get('color')

    if fecha_inicio:
        try:
            inicio = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            ventas = ventas.filter(fecha__gte=inicio)
        except ValueError:
            pass

    if fecha_fin:
        try:
            fin = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d'))
            ventas = ventas.filter(fecha__lt=fin + timezone.timedelta(days=1))
        except ValueError:
            pass

    if estado == 'activa':
        ventas = ventas.filter(anulada=False)
    elif estado == 'anulada':
        ventas = ventas.filter(anulada=True)

    if tipo_pago:
        ventas = ventas.filter(tipo_pago=tipo_pago)
    if tipo_documento:
        ventas = ventas.filter(tipo_documento=tipo_documento)
    if documento_cliente:
        ventas = ventas.filter(documento_cliente__icontains=documento_cliente)


    if producto_id:
        ventas = ventas.filter(detalleventa__producto__id=producto_id)
    if talla:
        ventas = ventas.filter(detalleventa__producto__talla=talla)
    if color:
        ventas = ventas.filter(detalleventa__producto__color=color)

    # Filtro por suma de cantidad de productos en la venta
    cantidad_producto = request.GET.get('cantidad_producto')
    if cantidad_producto:
        from django.db.models import Sum
        ventas = ventas.annotate(total_cantidad=Sum('detalleventa__cantidad')).filter(total_cantidad=int(cantidad_producto))

    ventas = ventas.order_by('-fecha')

    # Para los selects de producto, talla y color
    productos = Producto.objects.all().order_by('nombre')
    tallas = Producto.objects.exclude(talla__isnull=True).exclude(talla__exact='').values_list('talla', flat=True).distinct().order_by('talla')
    colores = Producto.objects.values_list('color', flat=True).distinct().order_by('color')

    # Exportación PDF sin template externo
    if request.GET.get('export') == 'pdf':
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; font-size: 11px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #888; padding: 6px; text-align: left; }
                th { background-color: #f2f2f2; }
                h2 { text-align: center; }
            </style>
        </head>
        <body>
            <h2>Reporte de Ventas</h2>
            <table>
                <thead>
                    <tr>
                        <th>Cliente</th>
                        <th>Doc.</th>
                        <th>Fecha</th>
                        <th>Total</th>
                        <th>Pago</th>
                        <th>Vuelto</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """
        for v in ventas:
            estado_txt = "Anulada" if v.anulada else "Activa"
            cliente_nombre = v.razon_social if v.tipo_comprobante == 'factura' else f"{v.nombres_cliente} {v.apellidos_cliente or ''}"
            html += f"""
            <tr>
                <td>{cliente_nombre}</td>
                <td>{v.tipo_documento.upper()} {v.documento_cliente}</td>
                <td>{django_date(v.fecha, "Y-m-d H:i")}</td>
                <td>S/ {v.total:.2f}</td>
                <td>{v.get_tipo_pago_display()}</td>
                <td>S/ {v.vuelto:.2f}</td>
                <td>{estado_txt}</td>
            </tr>
            """
        html += """
                </tbody>
            </table>
            <p style="text-align:right; margin-top: 30px;"><i>Exportado el """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """</i></p>
        </body>
        </html>
        """
        result = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=result)
        if pisa_status.err:
            return HttpResponse("Error generando PDF", status=500)

        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="ventas.pdf"'
        return response

    # Datos para gráficos (usando ventas filtradas)
    import json
    from django.utils import timezone
    hoy = timezone.now()
    meses_labels = []
    ventas_por_mes = []
    for i in range(5, -1, -1):
        mes = (hoy.replace(day=1) - timezone.timedelta(days=30*i))
        mes_label = mes.strftime('%b')
        meses_labels.append(mes_label)
        ventas_mes = ventas.filter(fecha__year=mes.year, fecha__month=mes.month).count()
        ventas_por_mes.append(ventas_mes)

    activa = ventas.filter(anulada=False).count()
    anulada = ventas.filter(anulada=True).count()
    efectivo = ventas.filter(tipo_pago='efectivo').count()
    tarjeta = ventas.filter(tipo_pago='tarjeta').count()
    ventas_distribucion = [activa, anulada, efectivo, tarjeta]

    return render(request, 'ventas/historial_ventas.html', {
        'ventas': ventas,
        'venta': Venta,
        'productos': productos,
        'tallas': tallas,
        'colores': colores,
        'ventas_por_mes': json.dumps(ventas_por_mes),
        'meses_labels': json.dumps(meses_labels),
        'ventas_distribucion': json.dumps(ventas_distribucion)
    })


@role_required('empleado')
def estadisticas_ventas(request):
    hoy = localtime(now()).date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    ventas_base = Venta.objects.filter(vendedor=request.user, anulada=False)
    ventas_filtradas = ventas_base
    filtro_aplicado = False
    try:
        if fecha_inicio and fecha_fin:
            fecha_inicio_dt = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            fecha_fin_dt = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1))
            ventas_filtradas = ventas_base.filter(fecha__gte=fecha_inicio_dt, fecha__lt=fecha_fin_dt)
            filtro_aplicado = True
        elif fecha_inicio:
            fecha_inicio_dt = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            ventas_filtradas = ventas_base.filter(fecha__gte=fecha_inicio_dt)
            filtro_aplicado = True
        elif fecha_fin:
            fecha_fin_dt = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1))
            ventas_filtradas = ventas_base.filter(fecha__lt=fecha_fin_dt)
            filtro_aplicado = True
    except ValueError:
        ventas_filtradas = ventas_base.none()
        filtro_aplicado = True

    # Totales correctos según filtro
    total_personalizado = ventas_filtradas.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    if filtro_aplicado:
        hoy = localtime(now()).date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        inicio_mes = hoy.replace(day=1)
        # Solo ventas dentro del rango filtrado Y del subrango correspondiente
        total_hoy = ventas_filtradas.filter(fecha__date=hoy).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        total_semana = ventas_filtradas.filter(fecha__date__gte=inicio_semana).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        total_mes = ventas_filtradas.filter(fecha__date__gte=inicio_mes).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    else:
        hoy = localtime(now()).date()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        inicio_mes = hoy.replace(day=1)
        total_hoy = ventas_filtradas.filter(fecha__date=hoy).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        total_semana = ventas_filtradas.filter(fecha__date__gte=inicio_semana).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        total_mes = ventas_filtradas.filter(fecha__date__gte=inicio_mes).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    # Lista de compras realizadas en el rango
    compras = ventas_filtradas.order_by('-fecha')

    return render(request, 'ventas/estadisticas_ventas.html', {
        'total_hoy': total_hoy,
        'total_semana': total_semana,
        'total_mes': total_mes,
        'total_personalizado': total_personalizado,
        'compras': compras,
        'filtro_aplicado': filtro_aplicado,
    })



