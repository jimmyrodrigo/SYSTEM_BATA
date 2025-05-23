from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from django.db.models import Sum, F
from .models import SolicitudAnulacionVenta, Venta, DetalleVenta, Caja
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
    usuario = request.user

    caja_abierta = Caja.objects.filter(usuario=usuario, esta_abierta=True).order_by('-fecha_apertura').first()
    if caja_abierta:
        caja_abierta.refresh_from_db()  
    caja_cerrada = Caja.objects.filter(usuario=usuario, esta_abierta=False).order_by('-fecha_cierre').first()

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'abrir':
            if caja_abierta:
                messages.error(request, "Ya tienes una caja abierta.")
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
                if caja_abierta.cierre_solicitado:
                    messages.info(request, "Ya solicitaste el cierre. Espera la aprobación del administrador.")
                else:
                    descripcion = request.POST.get('descripcion_cierre', '')
                    caja_abierta.cierre_solicitado = True
                    caja_abierta.descripcion_cierre = descripcion
                    caja_abierta.fecha_cierre = timezone.now()  # <- importante registrar fecha cierre
                    caja_abierta.esta_abierta = False         # <- marcar caja como cerrada
                    caja_abierta.save()
                    messages.success(request, "Solicitud de cierre enviada. Espera la aprobación del administrador.")
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
    talla_filtro = request.GET.get('talla', '').strip()
    marca_filtro = request.GET.get('marca', '')
    color_filtro = request.GET.get('color', '')
    categoria_filtro = request.GET.get('categoria', '')
    subcategoria_filtro = request.GET.get('subcategoria', '')

    productos = Producto.objects.all()

    if consulta:
        productos = productos.filter(nombre__icontains=consulta)
    if talla_filtro:
        productos = productos.filter(talla__icontains=talla_filtro)
    if marca_filtro:
        productos = productos.filter(marca__iexact=marca_filtro)
    if color_filtro:
        productos = productos.filter(color__iexact=color_filtro)
    if categoria_filtro:
        productos = productos.filter(categoria__nombre__iexact=categoria_filtro)
    if subcategoria_filtro:
        productos = productos.filter(subcategoria__nombre__iexact=subcategoria_filtro)
    
    talla = Producto.objects.values_list('talla', flat=True).distinct()
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

# productos es un queryset, cada producto tiene producto.talla
    return render(request, 'ventas/catalogo_productos.html', {
        'productos': productos,
        'marcas': marcas,
        'talla':talla,
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
        messages.info(request, "El carrito está vacío.")
        return redirect('catalogo_productos')

    productos = []
    total_final = Decimal('0.00')

    tipo_comprobante = request.POST.get('tipo_comprobante') if request.method == 'POST' else 'boleta'

    for producto_id, cantidad in carrito.items():
        producto = get_object_or_404(Producto, id=producto_id)
        if tipo_comprobante == 'boleta':
            precio_unitario_real = producto.precio / Decimal('1.18')  # Sin IGV
        else:
            precio_unitario_real = producto.precio  # Con IGV

        subtotal = precio_unitario_real * cantidad
        total_final += subtotal

        productos.append({
            'producto': producto,
            'cantidad': cantidad,
            'subtotal': subtotal,
            'precio_unitario_real': precio_unitario_real,
        })

    if tipo_comprobante == 'boleta':
        igv = Decimal('0.00')
        total_a_pagar = total_final
    else:
        igv = total_final * Decimal('0.18')
        total_a_pagar = total_final

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

@login_required
@role_required('empleado')
def ver_comprobante(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = venta.detalleventa_set.all()

    detalles_enriquecidos = []
    base = Decimal('0.00')

    for detalle in detalles:
        if venta.tipo_comprobante == "boleta":
            # Precio sin IGV = precio con IGV / 1.18
            precio_unitario_sin_igv = detalle.producto.precio / Decimal('1.18')
            subtotal = precio_unitario_sin_igv * detalle.cantidad
            base += subtotal    
        else:  # factura
            precio_unitario_sin_igv = detalle.producto.precio / Decimal('1.18')
            subtotal = precio_unitario_sin_igv * detalle.cantidad
            base += subtotal

        detalles_enriquecidos.append({
            'producto': detalle.producto,
            'cantidad': detalle.cantidad,
            'precio_unitario': precio_unitario_sin_igv,
            'subtotal': subtotal
        })

    # IGV solo para factura, en boleta IGV es 0
    igv = base * Decimal('0.18') if venta.tipo_comprobante == 'factura' else Decimal('0.00')

    context = {
        'venta': venta,
        'detalles': detalles_enriquecidos,
        'base': base,
        'igv': igv,
    }

    return render(request, 'ventas/comprobante_venta.html', context)

@role_required('empleado')
def descargar_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id, vendedor=request.user)
    detalles = venta.detalleventa_set.all()

    detalles_enriquecidos = []
    base = Decimal('0.00')

    for detalle in detalles:
        if venta.tipo_comprobante == "boleta":
            precio_unitario_sin_igv = detalle.producto.precio / Decimal('1.18')
            subtotal = precio_unitario_sin_igv * detalle.cantidad
            base += subtotal
        else:  # factura
            precio_unitario_sin_igv = detalle.producto.precio / Decimal('1.18')
            subtotal = precio_unitario_sin_igv * detalle.cantidad
            base += subtotal

        detalles_enriquecidos.append({
            'producto': detalle.producto,
            'cantidad': detalle.cantidad,
            'precio_unitario': precio_unitario_sin_igv,
            'subtotal': subtotal
        })
    igv = base * Decimal('0.18') if venta.tipo_comprobante == 'factura' else Decimal('0.00')

    razon_social = getattr(venta, 'razon_social', '') if venta.tipo_comprobante == 'factura' else ''

    # Ruta absoluta para xhtml2pdf
    logo_path = f"file://{os.path.join(settings.MEDIA_ROOT, 'image', 'logo.png')}"

    template = get_template('ventas/comprobante_venta.html')
    html = template.render({
        'venta': venta,
        'detalles': detalles_enriquecidos,
        'base': base,
        'igv': igv,
        'logo_path': logo_path,
        'razon_social': razon_social,
        
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=comprobante_{venta.id}.pdf'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=500)

    return response

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
        messages.success(request, "Solicitud de anulación enviada. Espera la aprobación del administrador.")
        return redirect('historial_ventas')

    return render(request, 'ventas/solicitar_anulacion.html', {'venta': venta})

# Anular venta



# views.py
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

    ventas = Venta.objects.filter(vendedor=request.user, anulada=False)

    # Filtro personalizado
    total_personalizado = None
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%d'))
            fecha_fin_dt = make_aware(datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1))
            total_personalizado = ventas.filter(
                fecha__gte=fecha_inicio_dt,
                fecha__lt=fecha_fin_dt
            ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        except ValueError:
            total_personalizado = 'error'

    # Totales normales
    total_hoy = ventas.filter(fecha__date=hoy).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    total_semana = ventas.filter(fecha__date__gte=inicio_semana).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    total_mes = ventas.filter(fecha__date__gte=inicio_mes).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    return render(request, 'ventas/estadisticas_ventas.html', {
        'total_hoy': total_hoy,
        'total_semana': total_semana,
        'total_mes': total_mes,
        'total_personalizado': total_personalizado,
    })



