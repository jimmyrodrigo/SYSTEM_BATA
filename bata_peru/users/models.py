# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

ROLES = (
    ('admin', 'Administrador'),
    ('empleado', 'Empleado de Ventas'),
    ('inventario', 'Jefe de Inventario'),
)

class UsuarioPersonalizado(AbstractUser):
    rol = models.CharField(max_length=20, choices=ROLES)
    tipo_documento = models.CharField(max_length=10, blank=True, null=True)
    numero_documento = models.CharField(max_length=15, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    token_admin = models.CharField(max_length=100, blank=True, null=True)

