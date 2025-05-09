from django import forms
from .models import UsuarioPersonalizado
from django.contrib.auth.forms import UserCreationForm

class RegistroForm(UserCreationForm):
    class Meta:
        model = UsuarioPersonalizado
        fields = ['username', 'password1', 'password2', 'rol', 'tipo_documento', 'numero_documento', 'fecha_nacimiento']
