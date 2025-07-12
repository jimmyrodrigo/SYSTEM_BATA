
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UsuarioPersonalizado
from .decorators import role_required
from datetime import datetime, date, timezone
from django.utils import timezone
from django.template import RequestContext
from django.http import JsonResponse
import requests
from bata_peru.inventario.models import Producto, Categoria
from bata_peru.ventas.views import catalogo_productos  # Importa la función con nombre más claro
from bata_peru.ventas.models import Caja, MovimientoCaja, SolicitudAnulacionVenta, SolicitudAperturaCaja, SolicitudCierreCaja  # Importa el modelo Caja para la función aprobar_cierre_caja
from bata_peru.ventas.admin_notifications import notificar_admin_solicitud

TOKEN_VALIDO = "BATA-2025-TOKEN"

# --- Vista para aprobar cierre de caja ---
@login_required
@role_required('admin')
def aprobar_cierre_caja(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCierreCaja, id=solicitud_id, estado='pendiente')
    caja = solicitud.caja
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'aprobar':
            # Marcar la solicitud como aprobada
            solicitud.estado = 'aprobada'
            solicitud.revisada_por = request.user
            solicitud.fecha_revision = timezone.now()
            solicitud.save()

            # Cerrar la caja
            caja.esta_abierta = False
            caja.cierre_aprobado = True
            caja.fecha_cierre = timezone.now()
            caja.save()

            # Notificar a los administradores por WebSocket (opcional)
            notificar_admin_solicitud('respuesta_cierre', {
                'tipo': 'cierre',
                'accion': 'aprobada',
                'usuario': caja.usuario.username,
                'caja_id': caja.id,
                'solicitud_id': solicitud.id,
                'fecha': str(solicitud.fecha_solicitud) if hasattr(solicitud, 'fecha_solicitud') else '',
            })

            # Si es AJAX, responder con JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Cierre de caja aprobado y caja cerrada correctamente.'
                })
            # Si no, redirigir como antes
            messages.success(request, 'Cierre de caja aprobado y caja cerrada correctamente.')
            return redirect('solicitudes_caja')
        elif accion == 'rechazar':
            # Marcar la solicitud como rechazada
            solicitud.estado = 'rechazada'
            solicitud.revisada_por = request.user
            solicitud.fecha_revision = timezone.now()
            solicitud.save()

            # Notificar a los administradores por WebSocket (opcional)
            notificar_admin_solicitud('respuesta_cierre', {
                'tipo': 'cierre',
                'accion': 'rechazada',
                'usuario': caja.usuario.username,
                'caja_id': caja.id,
                'solicitud_id': solicitud.id,
                'fecha': str(solicitud.fecha_solicitud) if hasattr(solicitud, 'fecha_solicitud') else '',
            })

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'info',
                    'message': 'Solicitud de cierre de caja rechazada.'
                })
            messages.info(request, 'Solicitud de cierre de caja rechazada.')
            return redirect('solicitudes_caja')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Acción no válida.'
                }, status=400)
            messages.error(request, 'Acción no válida.')
            return redirect('solicitudes_caja')
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Acceso inválido. Debe aprobar desde el formulario.'
            }, status=400)
        messages.error(request, 'Acceso inválido. Debe aprobar desde el formulario.')
        return redirect('solicitudes_caja')


def consultar_dni(request):
    dni = request.GET.get('dni')
    if not dni:
        return JsonResponse({'error': 'DNI requerido'}, status=400)

    try:
        headers = {'Authorization': 'Bearer apis-token-14733.6wytvSamJz7fsWerfsePwVPffD40Josu'}
        response = requests.get(f'https://api.apis.net.pe/v2/reniec/dni?numero={dni}', headers=headers)
        return JsonResponse(response.json())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
def login_view(request):
    if request.method == "POST":
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            if user.rol == 'admin':
                return redirect('admin_dashboard')
            elif user.rol == 'empleado':
                return redirect('catalogo_productos')
            elif user.rol == 'inventario':
                return redirect('catalogo_inventario')
            else:
                return redirect('login')
        else:
            messages.error(request, "Credenciales inválidas")  # Mensaje de error

    return render(request, 'registros/login.html')  # Renderiza el formulario en un GET


# --- Vista para solicitar anulación de venta (notifica a admin por WebSocket) ---

# --- Vista para solicitar anulación de venta (notifica a admin por WebSocket) ---

@csrf_exempt
@login_required
@role_required('empleado')
def solicitar_anulacion_venta(request, venta_id):
    if request.method == 'POST':
        from bata_peru.ventas.models import Venta
        venta = get_object_or_404(Venta, id=venta_id)
        # Evita duplicados
        if SolicitudAnulacionVenta.objects.filter(venta=venta, estado='pendiente').exists():
            return JsonResponse({'status': 'error', 'message': 'Ya existe una solicitud pendiente para esta venta.'}, status=400)
        solicitud = SolicitudAnulacionVenta.objects.create(
            venta=venta,
            usuario=request.user,
            estado='pendiente',
            fecha_solicitud=timezone.now()
        )
        # Notificar a los administradores por WebSocket
        notificar_admin_solicitud('nueva_anulacion', {
            'tipo': 'anulacion',
            'usuario': request.user.username,
            'venta_id': venta.id,
            'solicitud_id': solicitud.id,
            'fecha': str(solicitud.fecha_solicitud),
        })
        return JsonResponse({'status': 'ok', 'message': 'Solicitud de anulación enviada'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def aprobar_anulacion_venta(request, solicitud_id):

    import logging
    logger = logging.getLogger("django")
    logger.warning(f"[ANULACION] POST recibido para solicitud {solicitud_id}")
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAnulacionVenta, id=solicitud_id)
        venta = solicitud.venta
        caja = Caja.objects.filter(usuario=venta.vendedor, esta_abierta=True).last()

        if not caja:
            logger.warning(f"[ANULACION] No hay caja abierta para {venta.vendedor}")
            messages.error(request, "No hay una caja abierta para actualizar.")
            return redirect('revisar_solicitudes_anulacion')

        if not venta.anulada:
            logger.warning(f"[ANULACION] Anulando venta {venta.id} y ajustando caja {caja.id}")
            # Anular venta
            venta.anulada = True
            venta.save()

            # Ajustar caja
            caja.ingresos -= venta.total
            caja.egresos -= venta.vuelto
            caja.saldo_final = caja.saldo_inicial + caja.ingresos 
            caja.save()

            solicitud.estado = 'aprobada'
            solicitud.revisada_por = request.user
            solicitud.fecha_revision = timezone.now()
            solicitud.save()

            # Notificar a los administradores por WebSocket
            notificar_admin_solicitud('respuesta_anulacion', {
                'tipo': 'anulacion',
                'accion': 'aprobada',
                'usuario': venta.vendedor.username,
                'monto': str(venta.total),
                'solicitud_id': solicitud.id,
                'fecha': str(solicitud.fecha_solicitud) if hasattr(solicitud, 'fecha_solicitud') else '',
            })

            messages.success(request, "Venta anulada y caja actualizada correctamente.")
        else:
            logger.warning(f"[ANULACION] Venta {venta.id} ya estaba anulada")
            messages.warning(request, "La venta ya estaba anulada.")

        return redirect('revisar_solicitudes_anulacion')
    else:
        logger.warning(f"[ANULACION] Acceso inválido a aprobar_anulacion_venta (no POST)")
        messages.error(request, "Acceso inválido. Debe aprobar desde el formulario.")
        return redirect('revisar_solicitudes_anulacion')
         
@login_required
@role_required('admin')
def movimiento_caja(request):
    # Obtener todas las cajas (puedes filtrar por usuario o fechas si quieres)
    cajas = Caja.objects.select_related('usuario').order_by('-fecha_apertura')
    
    # Obtener movimientos para la primera caja abierta o la última cerrada como ejemplo
    movimientos = MovimientoCaja.objects.select_related('caja').order_by('-fecha')
    
    # Notificar a los administradores por WebSocket cada vez que se consulta movimientos (puedes ajustar la lógica según tu flujo)
    from bata_peru.ventas.admin_notifications import notificar_admin_solicitud
    notificar_admin_solicitud('nueva_movimiento', {
        'tipo': 'movimiento',
        'accion': 'consulta',
        'cantidad': movimientos.count(),
        'fecha': str(timezone.now()),
    })
    context = {
        'cajas': cajas,
        'movimientos': movimientos,
    }
    return render(request, 'users/movimiento_caja.html', context)

@login_required
@role_required('admin')
def solicitudes_caja(request):
    # Solicitudes de cierre de caja (ahora correctamente usando el modelo de solicitudes)
    from bata_peru.ventas.models import SolicitudCierreCaja
    solicitudes_cierre = SolicitudCierreCaja.objects.filter(estado='pendiente')

    # Solicitudes de apertura de caja
    solicitudes_apertura = SolicitudAperturaCaja.objects.filter(estado='pendiente')

    return render(request, 'users/solicitudes_caja.html', {
        'solicitudes_cierre': solicitudes_cierre,
        'solicitudes_apertura': solicitudes_apertura
    })

# --- ENDPOINTS PARA NOTIFICACIONES DE NUEVAS SOLICITUDES ---
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
@role_required('admin')
def notificar_nueva_apertura(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        from bata_peru.ventas.admin_notifications import notificar_admin_solicitud
        notificar_admin_solicitud('nueva_apertura', {
            'event': 'nueva_apertura',
            'usuario': data.get('usuario', ''),
            'monto_inicial': str(data.get('monto_inicial', '')),
            'comentario': data.get('comentario', ''),
            'fecha': data.get('fecha', '')
        })
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
@login_required
@role_required('admin')
def notificar_nueva_cierre(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        from bata_peru.ventas.admin_notifications import notificar_admin_solicitud
        notificar_admin_solicitud('nueva_cierre', {
            'event': 'nueva_cierre',
            'usuario': data.get('usuario', ''),
            'comentario': data.get('comentario', ''),
            'fecha': data.get('fecha', '')
        })
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
@role_required('admin')
def solicitudes_apertura_caja(request):
    solicitudes = SolicitudAperturaCaja.objects.filter(estado='pendiente')
    return render(request, 'users/solicitudes_caja.html', {'solicitudes': solicitudes})


@login_required
@role_required('admin')
def aprobar_apertura_caja(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudAperturaCaja, id=solicitud_id, estado='pendiente')


    if request.method == 'POST':
        from bata_peru.ventas.utils import notificar_usuario
        accion = request.POST.get('accion')

        if accion == 'aprobar':
            # Crear una nueva caja para el usuario
            caja = Caja.objects.create(
                usuario=solicitud.usuario,
                fecha_apertura=timezone.now(),
                saldo_inicial=solicitud.monto_inicial,
                ingresos=0,
                egresos=0,
                saldo_final=solicitud.monto_inicial,
                esta_abierta=True
            )

            # Actualizar el estado de la solicitud
            solicitud.estado = 'aprobada'
            solicitud.save()

            # Notificar al usuario por WebSocket
            notificar_usuario(solicitud.usuario.username, 'aprobada')

            # Notificar a los administradores por WebSocket
            notificar_admin_solicitud('respuesta_apertura', {
                'tipo': 'usuario',
                'accion': 'aprobada',
                'usuario': solicitud.usuario.username,
                'monto': str(solicitud.monto_inicial),
                'solicitud_id': solicitud.id,
                'fecha': str(solicitud.fecha_solicitud) if hasattr(solicitud, 'fecha_solicitud') else '',
            })

            # Mensaje de éxito que se mostrará en el template
            response = {
                'status': 'success',
                'message': f"Solicitud de apertura de caja para {solicitud.usuario.username} aprobada.",
                'nuevo_estado': 'Aprobada'
            }
        elif accion == 'rechazar':
            # Actualizar el estado de la solicitud
            solicitud.estado = 'rechazada'
            solicitud.save()

            # Notificar al usuario por WebSocket
            notificar_usuario(solicitud.usuario.username, 'rechazada')

            # Notificar a los administradores por WebSocket
            notificar_admin_solicitud('respuesta_apertura', {
                'tipo': 'usuario',
                'accion': 'rechazada',
                'usuario': solicitud.usuario.username,
                'monto': str(solicitud.monto_inicial),
                'solicitud_id': solicitud.id,
                'fecha': str(solicitud.fecha_solicitud) if hasattr(solicitud, 'fecha_solicitud') else '',
            })

            # Mensaje de rechazo que se mostrará en el template
            response = {
                'status': 'info',
                'message': f"Solicitud de apertura de caja para {solicitud.usuario.username} rechazada.",
                'nuevo_estado': 'Rechazada'
            }

        # Enviar la respuesta en formato JSON para actualizar dinámicamente
        return JsonResponse(response)

    # Si no es un POST, redirigir de nuevo a la página de solicitudes
    return redirect('solicitudes_caja')




# users/views.py

@login_required
@role_required('empleado')
def ventas_dashboard(request):
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
    from .models import UsuarioPersonalizado
    admin_user = UsuarioPersonalizado.objects.filter(rol='admin').first()
    context = {
        'productos': productos,
        'categorias': categorias,
        'tallas': tallas,
        'marcas': marcas,
        'colores': colores,
        'admin_user': admin_user
    }
    return render(request, 'ventas/base_dashboard.html', context)

# Vista para el catálogo de inventario
@role_required('inventario')
def catalogo_inventario(request):
    return render(request, 'inventario/catalogo_inventario.html')

@role_required('admin')
def admin_dashboard(request):
    nombre_admin = request.user.username
    solicitudes_count = Caja.objects.filter(cierre_solicitado=True, cierre_aprobado=False, esta_abierta=True).count()
    solicitudes_anulacion_count = SolicitudAnulacionVenta.objects.filter(estado='pendiente').count()
    from .models import UsuarioPersonalizado
    usuarios_cajero = UsuarioPersonalizado.objects.filter(rol='empleado')
    return render(request, 'users/dashboard_admin.html', {
        'solicitudes_count': solicitudes_count,
        'solicitudes_anulacion_count': solicitudes_anulacion_count,
        'nombre_admin': nombre_admin,
        'usuarios_cajero': usuarios_cajero
    })

@role_required('admin')
def revisar_solicitudes_anulacion(request):
    solicitudes = SolicitudAnulacionVenta.objects.filter(estado='pendiente').order_by('fecha_solicitud')
    return render(request, 'users/solicitudes_anulacion.html', {'solicitudes': solicitudes})




@role_required('admin')
def gestion_usuarios(request):
    usuarios = UsuarioPersonalizado.objects.exclude(username=request.user.username)
    return render(request, 'users/gestion_usuario.html', {'usuarios': usuarios})
