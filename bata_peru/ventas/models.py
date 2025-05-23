from django.db import models
from django.contrib.auth import get_user_model
from inventario.models import Producto
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

class Venta(models.Model):
    TIPO_COMPROBANTE_CHOICES = [
        ('boleta', 'Boleta'),
        ('factura', 'Factura'),
    ]

    TIPO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta de crédito'),
        ('yape', 'Yape'),
        ('plin', 'Plin'),
    ]

    TIPO_DOCUMENTO_CHOICES = [
        ('dni', 'DNI'),
        ('ruc', 'RUC'),
        ('ce', 'Carné de extranjería'),
        ('pasaporte', 'Pasaporte'),
    ]

    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO_CHOICES)
    tipo_comprobante = models.CharField(max_length=20, choices=TIPO_COMPROBANTE_CHOICES)
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES, default='dni')
    nombres_cliente = models.CharField(max_length=100)
    razon_social = models.CharField(max_length=100, blank=True, null=True)
    apellidos_cliente = models.CharField(max_length=100, blank=True, null=True)
    documento_cliente = models.CharField(max_length=20)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vuelto = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fecha = models.DateTimeField(auto_now_add=True)
    vendedor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    anulada = models.BooleanField(default=False)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def calcular_total(self):
        return sum(detalle.subtotal() for detalle in self.detalleventa_set.all())

    def __str__(self):
        return f"{self.get_tipo_comprobante_display()} - {self.nombres_cliente} - {self.fecha.strftime('%Y-%m-%d')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    def subtotal(self):
        return self.producto.precio * self.cantidad

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"


class Caja(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    esta_abierta = models.BooleanField(default=True)

    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    ingresos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    egresos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cierre_solicitado = models.BooleanField(default=False)
    cierre_aprobado = models.BooleanField(default=False)
    aprobado_por = models.ForeignKey(
        User, null=True, blank=True, related_name='aprobaciones_cierre', on_delete=models.SET_NULL
    )
    descripcion_cierre = models.TextField(blank=True)
    def calcular_total(self):
        return self.saldo_inicial + self.ingresos - self.egresos

    def __str__(self):
        return f"Caja de {self.usuario.username} ({'Abierta' if self.esta_abierta else 'Cerrada'})"
    
    def cerrar(self, usuario_aprobador):
        self.cierre_aprobado = True
        self.aprobado_por = usuario_aprobador
        self.fecha_cierre = timezone.now()
        self.esta_abierta = False
        self.saldo_final = self.saldo_inicial + self.ingresos - self.egresos
        self.save()
        
class MovimientoCaja(models.Model):
    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]

    caja = models.ForeignKey(Caja, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo.upper()} - S/ {self.monto} ({self.descripcion})"

class SolicitudAnulacionVenta(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    usuario_solicitante = models.ForeignKey(User, on_delete=models.CASCADE)
    comentario = models.TextField()
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    revisada_por = models.ForeignKey(
        User, null=True, blank=True, related_name='anulaciones_revisadas', on_delete=models.SET_NULL
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Solicitud Anulación Venta {self.venta.id} - {self.usuario_solicitante.username} ({self.get_estado_display()})"
