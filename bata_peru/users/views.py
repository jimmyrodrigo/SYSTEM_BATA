from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import UsuarioPersonalizado
from .decorators import role_required
from datetime import datetime, date
from django.http import JsonResponse

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
            fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Fecha de nacimiento inválida")
            return redirect('registro')

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

@role_required('admin')
def admin_dashboard(request):
    return render(request, 'users/dashboard_admin.html')

@role_required('admin')
def gestion_usuarios(request):
    usuarios = UsuarioPersonalizado.objects.exclude(username=request.user.username)
    return render(request, 'users/gestion_usuarios.html', {'usuarios': usuarios})
