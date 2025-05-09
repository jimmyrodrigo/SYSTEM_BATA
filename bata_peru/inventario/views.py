from django.contrib.auth.decorators import login_required
from users.decorators import role_required
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db.models import F
from django.utils.dateparse import parse_date
from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto
from .forms import ProductoForm
from django.contrib import messages

@role_required('empleado')
def inventario_dashboard(request):
    return redirect('catalogo_inventario')
    
@role_required('inventario')
def catalogo_inventario(request):
    consulta = request.GET.get('buscar', '')
    marca_filtro = request.GET.get('marca', '')
    color_filtro = request.GET.get('color', '')
    categoria_filtro = request.GET.get('categoria', '')
    subcategoria_filtro = request.GET.get('subcategoria', '')
    fecha_ingreso = request.GET.get('fecha_ingreso', '')
    stock_bajo = request.GET.get('stock_bajo', '')

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
    if fecha_ingreso:
        fecha = parse_date(fecha_ingreso)
        if fecha:
            productos = productos.filter(fecha_ingreso=fecha)
    if stock_bajo == 'on':
        productos = productos.filter(cantidad__lte=F('stock_minimo'))

    marcas = Producto.objects.values_list('marca', flat=True).distinct()
    colores = Producto.objects.values_list('color', flat=True).distinct()
    categorias = Producto.objects.values_list('categoria__nombre', flat=True).distinct()
    subcategorias = Producto.objects.values_list('subcategoria__nombre', flat=True).distinct()

    return render(request, 'inventario/catalogo_inventario.html', {
        'productos': productos,
        'marcas': marcas,
        'colores': colores,
        'categorias': categorias,
        'subcategorias': subcategorias,
    })

@role_required('inventario')
def agregar_producto(request):
    form = ProductoForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid():
            categoria = form.cleaned_data.get('categoria')
            subcategoria = form.cleaned_data.get('subcategoria')
            cantidad = form.cleaned_data.get('cantidad')

            if subcategoria and subcategoria.categoria != categoria:
                form.add_error('subcategoria', '❌ Esta subcategoría no pertenece a la categoría seleccionada.')

            elif cantidad < 5:
                form.add_error('cantidad', '❌ La cantidad inicial debe ser al menos 5 unidades.')

            else:
                form.save()
                messages.success(request, '✅ Producto agregado con éxito.')
                return redirect('catalogo_inventario')

    return render(request, 'inventario/agregar_producto.html', {'form': form})


@role_required('inventario')
def control_stock_minimo(request):
    productos_bajos = Producto.objects.filter(cantidad__lte=F('stock_minimo'))

    if productos_bajos.exists():
        messages.warning(request, '⚠️ Hay productos con stock por debajo del mínimo permitido.')
    else:
        messages.success(request, '✅ Todos los productos tienen stock suficiente.')

    return render(request, 'inventario/control_stock.html', {'productos_bajos': productos_bajos})


@role_required('inventario')
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)

    if request.method == 'POST':
        if form.is_valid():
            categoria = form.cleaned_data.get('categoria')
            subcategoria = form.cleaned_data.get('subcategoria')

            if subcategoria and subcategoria.categoria != categoria:
                form.add_error('subcategoria', '❌ Esta subcategoría no pertenece a la categoría seleccionada.')
            else:
                form.save()
                messages.success(request, '✅ Producto actualizado correctamente.')
                return redirect('catalogo_inventario')  # Solo redirige si todo está bien

    # En caso de GET o si el form tiene errores
    return render(request, 'inventario/editar_producto.html', {
        'form': form,
        'producto': producto
    })





@role_required('inventario')
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.delete()
    return redirect('catalogo_inventario')

@role_required('inventario')
def actualizar_stock(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        nueva_cantidad = request.POST.get('cantidad')
    if nueva_cantidad.isdigit() and int(nueva_cantidad) >= 0:
        producto.cantidad = int(nueva_cantidad)
        producto.save()

    return redirect('catalogo_inventario')
