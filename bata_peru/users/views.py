from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UsuarioPersonalizado
from .decorators import role_required
from datetime import datetime, date, timezone
from django.utils import timezone
from django.http import JsonResponse
import requests  # Import necesario para hacer peticiones HTTP

from ventas.models import Caja, SolicitudAnulacionVenta  # Importa el modelo Caja para la función aprobar_cierre_caja

TOKEN_VALIDO = "BATA-2025-TOKEN"


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


def home_view(request):
    if request.user.is_authenticated:
        if request.user.rol == 'admin':
            return redirect('admin_dashboard')
        elif request.user.rol == 'empleado':
            return redirect('ventas_dashboard')
        elif request.user.rol == 'inventario':
            return redirect('catalogo_inventario')
    return redirect('login')


def login_view(request):
    if request.method == "POST":
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            if user.rol == 'admin':
                return redirect('admin_dashboard')
            elif user.rol == 'empleado':
                return redirect('ventas_dashboard')
            elif user.rol == 'inventario':
                return redirect('catalogo_inventario')
        else:
            messages.error(request, "Credenciales inválidas")
    return render(request, 'registros/login.html')


def calcular_edad(fecha_nacimiento):
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))


def registro_view(request):
    if request.method == "POST":
        token = request.POST.get('token')
        if token != TOKEN_VALIDO:
            messages.error(request, "Token inválido")
            return redirect('registro')

        username = request.POST.get('username')
        password = request.POST.get('password')
        rol = request.POST.get('rol')
        tipo_documento = request.POST.get('tipo_documento')
        numero_documento = request.POST.get('numero_documento')
        fecha_nacimiento_str = request.POST.get('fecha_nacimiento')

        if UsuarioPersonalizado.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya está en uso")
            return redirect('registro')

        try:
            fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, "%d/%m/%Y").date()
        except ValueError:
            fecha_nacimiento = None
            messages.error(request, "Formato de fecha inválido, use DD/MM/AAAA")

        edad = calcular_edad(fecha_nacimiento)
        if edad < 18:
            messages.error(request, "Debes ser mayor de 18 años para registrarte.")
            return redirect('registro')

        UsuarioPersonalizado.objects.create_user(
            username=username,
            password=password,
            rol=rol,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            fecha_nacimiento=fecha_nacimiento
        )

        messages.success(request, "Usuario creado correctamente")
        return redirect('login')

    return render(request, 'registros/registro.html')

@login_required
@role_required('admin')
def solicitudes_cierre_caja(request):
    solicitudes = Caja.objects.filter(cierre_solicitado=True, cierre_aprobado=False, esta_abierta=True)
    return render(request, 'users/solicitudes_cierre_caja.html', {'solicitudes': solicitudes})

@login_required
@role_required('admin')
def aprobar_cierre_caja(request, caja_id):
    caja = get_object_or_404(Caja, id=caja_id, cierre_solicitado=True, cierre_aprobado=False, esta_abierta=True)

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'aprobar':
            caja.cerrar(request.user)  # usa método del modelo
            messages.success(request, f"Cierre de caja de {caja.usuario.username} aprobado.")
        elif accion == 'rechazar':
            caja.cierre_solicitado = False
            caja.descripcion_cierre = ''
            caja.save()
            messages.info(request, f"Solicitud de cierre de caja de {caja.usuario.username} rechazada.")
        return redirect('solicitudes_cierre_caja')

    return render(request, 'ventas/aprobar_cierre_caja.html', {'caja': caja})


@role_required('admin')
def admin_dashboard(request):
    solicitudes_count = Caja.objects.filter(cierre_solicitado=True, cierre_aprobado=False, esta_abierta=True).count()
    solicitudes_anulacion_count = SolicitudAnulacionVenta.objects.filter(estado='pendiente').count()
    return render(request, 'users/dashboard_admin.html', {
        'solicitudes_count': solicitudes_count,
        'solicitudes_anulacion_count': solicitudes_anulacion_count
    })

@role_required('admin')
def revisar_solicitudes_anulacion(request):
    solicitudes = SolicitudAnulacionVenta.objects.filter(estado='pendiente').order_by('fecha_solicitud')
    return render(request, 'users/solicitudes_anulacion.html', {'solicitudes': solicitudes})


@role_required('admin')
def aprobar_anulacion_venta(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudAnulacionVenta, id=solicitud_id)
    venta = solicitud.venta
    caja = Caja.objects.filter(usuario=venta.vendedor, esta_abierta=True).last()

    if not caja:
        messages.error(request, "No hay una caja abierta para actualizar.")
        return redirect('revisar_solicitudes_anulacion')

    if not venta.anulada:
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

        messages.success(request, "Venta anulada y caja actualizada correctamente.")
    else:
        messages.warning(request, "La venta ya estaba anulada.")

    return redirect('revisar_solicitudes_anulacion')

@role_required('admin')
def gestion_usuarios(request):
    usuarios = UsuarioPersonalizado.objects.exclude(username=request.user.username)
    return render(request, 'users/gestion_usuario.html', {'usuarios': usuarios})
