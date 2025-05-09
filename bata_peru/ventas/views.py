from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from django.db.models import Sum, F
from .models import Venta, DetalleVenta, Caja
from django.utils.timezone import now, localtime, make_aware
from datetime import datetime, timedelta
from django.db.models import Sum, F, Q
from ventas.models import DetalleVenta, Venta
from inventario.models import Producto
from users.decorators import role_required
from xhtml2pdf import pisa
import os
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse
import requests
from django.contrib.auth.decorators import login_required

@login_required
@role_required('empleado')
def caja_usuario(request):
    hoy = timezone.now().date()
    usuario = request.user

    caja_abierta = Caja.objects.filter(usuario=usuario, fecha_apertura__date=hoy, esta_abierta=True).first()
    caja_cerrada = Caja.objects.filter(usuario=usuario, fecha_apertura__date=hoy, esta_abierta=False).first()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'abrir':
            if caja_abierta:
                messages.error(request, "Ya tienes una caja abierta hoy.")
            else:
                monto_inicial = request.POST.get('monto_inicial')
                try:
                    monto_inicial = float(monto_inicial)
                    if monto_inicial < 0:
                        raise ValueError
                except:
                    messages.error(request, "Monto inicial inválido")
                    return redirect('caja_usuario')

                Caja.objects.create(
                    usuario=usuario,
                    fecha_apertura=timezone.now(),
                    saldo_inicial=monto_inicial,
                    ingresos=0,
                    egresos=0,
                    saldo_final=monto_inicial,
                    esta_abierta=True
                )
                messages.success(request, "✅ Caja abierta correctamente.")
                return redirect('caja_usuario')

        elif accion == 'cerrar':
            if not caja_abierta:
                messages.error(request, "No tienes una caja abierta para cerrar.")
            else:
                caja_abierta.fecha_cierre = timezone.now()
                caja_abierta.esta_abierta = False
                caja_abierta.saldo_final = caja_abierta.saldo_inicial + caja_abierta.ingresos - caja_abierta.egresos
                caja_abierta.save()
                messages.success(request, "✅ Caja cerrada correctamente.")
                return redirect('caja_usuario')

    context = {
        'caja_abierta': caja_abierta,
        'caja_cerrada': caja_cerrada,
    }
    return render(request, 'ventas/caja_usuario.html', context)

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

def consultar_ruc(request):
    ruc = request.GET.get('ruc')
    if not ruc:
        return JsonResponse({'error': 'RUC requerido'}, status=400)

    try:
        headers = {
            'Authorization': 'Bearer apis-token-14733.6wytvSamJz7fsWerfsePwVPffD40Josu'
        }
        response = requests.get(f'https://api.apis.net.pe/v2/sunat/ruc?numero={ruc}', headers=headers)
        data = response.json()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@role_required('empleado')
def ventas_dashboard(request):
    return redirect('catalogo_productos')

# Catálogo de productos con filtros y carrito
@role_required('empleado')
def catalogo_productos(request):
    consulta = request.GET.get('buscar', '')
    marca_filtro = request.GET.get('marca', '')
    color_filtro = request.GET.get('color', '')
    categoria_filtro = request.GET.get('categoria', '')
    subcategoria_filtro = request.GET.get('subcategoria', '')

    productos = Producto.objects.all()

    if consulta:
        productos = productos.filter(nombre__icontains=consulta)
    if marca_filtro:
        productos = productos.filter(marca__iexact=marca_filtro)
    if color_filtro:
        productos = productos.filter(color__iexact=color_filtro)
    if categoria_filtro:
        productos = productos.filter(categoria__nombre__iexact=categoria_filtro)

    if subcategoria_filtro:
        productos = productos.filter(subcategoria__nombre__iexact=subcategoria_filtro)


    marcas = Producto.objects.values_list('marca', flat=True).distinct()
    colores = Producto.objects.values_list('color', flat=True).distinct()
    categorias = Producto.objects.values_list('categoria__nombre', flat=True).distinct()
    subcategorias = Producto.objects.values_list('subcategoria__nombre', flat=True).distinct()

    carrito = request.session.get('carrito', {})
    carrito_items = []
    subtotal = Decimal('0.00')

    for producto_id, cantidad in carrito.items():
        producto = get_object_or_404(Producto, id=producto_id)
        total_item = producto.precio * cantidad
        subtotal += total_item
        carrito_items.append({
            'producto': producto,
            'cantidad': cantidad,
            'total': total_item
        })

    total = subtotal
    base_sin_igv = total / Decimal('1.18') if total else Decimal('0.00')
    igv = total - base_sin_igv

    return render(request, 'ventas/catalogo_productos.html', {
        'productos': productos,
        'marcas': marcas,
        'colores': colores,
        'categorias': categorias,
        'subcategorias': subcategorias,
        'carrito_items': carrito_items,
        'subtotal': base_sin_igv,
        'igv': igv,
        'total': total,
    })

@role_required('empleado')
def agregar_al_carrito(request, producto_id):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id=producto_id)
        cantidad = int(request.POST.get('cantidad', 1))

        carrito = request.session.get('carrito', {})
        carrito[str(producto_id)] = carrito.get(str(producto_id), 0) + cantidad

        request.session['carrito'] = carrito
        messages.success(request, f"{producto.nombre} agregado al carrito.")

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
    return redirect('catalogo_productos')


@login_required
@role_required('empleado')
def realizar_compra(request):
    carrito = request.session.get('carrito', {})

    if not carrito:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect('catalogo_productos')

    productos = []
    total_final = Decimal('0.00')

    for producto_id, cantidad in carrito.items():
        producto = get_object_or_404(Producto, id=producto_id)
        subtotal = producto.precio * cantidad
        total_final += subtotal
        productos.append({
            'producto': producto,
            'cantidad': cantidad,
            'subtotal': subtotal,
        })

    base_sin_igv = total_final / Decimal('1.18')
    igv = total_final - base_sin_igv

    if request.method == 'POST':
        tipo_comprobante = request.POST.get('tipo_comprobante')
        tipo_pago = request.POST.get('tipo_pago')
        tipo_documento = request.POST.get('tipo_documento')
        documento = request.POST.get('documento_cliente')
        monto_pagado = Decimal(request.POST.get('monto_pagado', '0'))

        # Validaciones de documento
        if tipo_documento == 'dni' and len(documento) != 8:
            messages.error(request, "El DNI debe tener 8 dígitos.")
            return redirect('realizar_compra')
        elif tipo_documento == 'ruc' and len(documento) != 11:
            messages.error(request, "El RUC debe tener 11 dígitos.")
            return redirect('realizar_compra')
        elif tipo_documento == 'ce' and len(documento) < 8:
            messages.error(request, "El carné de extranjería debe tener al menos 8 caracteres.")
            return redirect('realizar_compra')

        # Cliente según comprobante
        if tipo_comprobante == 'factura':
            nombres = request.POST.get('razon_social')
            apellidos = ""
        else:
            nombres = request.POST.get('nombres_cliente')
            apellidos = request.POST.get('apellidos_cliente')

        # Verificar caja abierta
        caja = Caja.objects.filter(usuario=request.user, esta_abierta=True).last()
        if not caja:
            messages.error(request, "No hay una caja abierta actualmente.")
            return redirect('realizar_compra')

        # Validar vuelto
        if tipo_pago == 'efectivo':
            if monto_pagado < total_final:
                messages.error(request, "El monto pagado no cubre el total.")
                return redirect('realizar_compra')
            vuelto = monto_pagado - total_final
            if vuelto > caja.saldo_final:
                messages.error(request, f"No se puede completar la venta. El vuelto de S/ {vuelto:.2f} excede el saldo disponible en caja.")
                return redirect('realizar_compra')
        else:
            vuelto = Decimal('0.00')
            monto_pagado = total_final

        # Crear venta
        venta = Venta.objects.create(
            vendedor=request.user,
            nombres_cliente=nombres,
            apellidos_cliente=apellidos,
            documento_cliente=documento,
            tipo_documento=tipo_documento,
            tipo_comprobante=tipo_comprobante,
            tipo_pago=tipo_pago,
            total=total_final,
            fecha=timezone.now()
        )

        for item in productos:
            producto = item['producto']
            cantidad = item['cantidad']
            if producto.cantidad < cantidad:
                messages.error(request, f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.cantidad}")
                return redirect('realizar_compra')

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad
            )
            producto.cantidad -= cantidad
            producto.save()

        # Actualizar caja
        caja.ingresos += total_final
        caja.egresos += vuelto
        caja.saldo_final += (monto_pagado - vuelto)
        caja.save()

        del request.session['carrito']
        messages.success(request, f"Venta registrada. Vuelto: S/ {vuelto:.2f}")
        return redirect('ver_comprobante', venta_id=venta.id)

    return render(request, 'ventas/realizar_compra.html', {
        'productos': productos,
        'igv': igv,
        'total_final': total_final,
        'total': base_sin_igv,
    })

# Ver comprobante
@role_required('empleado')
def ver_comprobante(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, vendedor=request.user)
    base = venta.total / Decimal('1.18')
    igv = venta.total - base

    return render(request, 'ventas/comprobante_venta.html', {
        'venta': venta,
        'base': base,
        'igv': igv,
    })

# Descargar comprobante en PDF
@role_required('empleado')
def descargar_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, vendedor=request.user)
    
    total = venta.total
    base = total / Decimal('1.18')
    igv = total - base

    # Ruta absoluta para xhtml2pdf
    logo_path = f"file://{os.path.join(settings.MEDIA_ROOT, 'image', 'logo.png')}"

    template = get_template('ventas/comprobante_venta.html')
    html = template.render({
        'venta': venta,
        'base': base,
        'igv': igv,
        'logo_path': logo_path,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=comprobante_{venta.id}.pdf'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)

    return response

# Anular venta
@role_required('empleado')
def anular_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, vendedor=request.user)

    if not venta.anulada:
        venta.anulada = True
        venta.save()
        messages.success(request, "La venta fue anulada correctamente.")
    else:
        messages.warning(request, "La venta ya estaba anulada.")

    return redirect('historial_ventas')

@role_required('empleado')
def historial_ventas(request):
    ventas = Venta.objects.filter(vendedor=request.user)

    # --- FILTROS ---
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')

    if fecha_inicio:
        try:
            inicio = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            ventas = ventas.filter(fecha__gte=inicio)
        except ValueError:
            pass

    if fecha_fin:
        try:
            fin = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d'))
            # Aumentamos un día completo para incluir toda la fecha de fin
            ventas = ventas.filter(fecha__lt=fin + timezone.timedelta(days=1))
        except ValueError:
            pass

    if estado == 'activa':
        ventas = ventas.filter(anulada=False)
    elif estado == 'anulada':
        ventas = ventas.filter(anulada=True)

    ventas = ventas.order_by('-fecha')  # Más recientes primero

    return render(request, 'ventas/historial_ventas.html', {
        'ventas': ventas
    })

@role_required('empleado')
def estadisticas_ventas(request):
    hoy = localtime(now()).date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    detalles = DetalleVenta.objects.filter(
        venta__vendedor=request.user,
        venta__anulada=False
    )

    # FILTRO PERSONALIZADO
    total_personalizado = None
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            fecha_fin_dt = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1))
            total_personalizado = detalles.filter(
                venta__fecha__gte=fecha_inicio_dt,
                venta__fecha__lt=fecha_fin_dt
            ).aggregate(total=Sum(F('producto__precio') * F('cantidad')))['total'] or 0
        except ValueError:
            total_personalizado = 'error'

    # TOTALES NORMALES
    total_hoy = detalles.filter(
        venta__fecha__date=hoy
    ).aggregate(total=Sum(F('producto__precio') * F('cantidad')))['total'] or 0

    total_semana = detalles.filter(
        venta__fecha__date__gte=inicio_semana
    ).aggregate(total=Sum(F('producto__precio') * F('cantidad')))['total'] or 0

    total_mes = detalles.filter(
        venta__fecha__date__gte=inicio_mes
    ).aggregate(total=Sum(F('producto__precio') * F('cantidad')))['total'] or 0

    return render(request, 'ventas/estadisticas_ventas.html', {
        'total_hoy': total_hoy,
        'total_semana': total_semana,
        'total_mes': total_mes,
        'total_personalizado': total_personalizado,
    })


