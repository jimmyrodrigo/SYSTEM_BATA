from django.contrib import admin
from .models import UsuarioPersonalizado

@admin.register(UsuarioPersonalizado)
class UsuarioPersonalizado(admin.ModelAdmin):
    lisst_display = ('id', "rol", "tipo_documento")