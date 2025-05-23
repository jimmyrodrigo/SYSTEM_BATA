from django import forms
from .models import Venta

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = [
            'tipo_pago',
            'tipo_comprobante',
            'nombres_cliente',
            'apellidos_cliente',
            'documento_cliente',
            'razon_social'
        ]
        widgets = {
            'tipo_pago': forms.Select(attrs={'class': 'w-full rounded'}),
            'tipo_comprobante': forms.Select(attrs={'class': 'w-full rounded'}),
            'nombres_cliente': forms.TextInput(attrs={'class': 'w-full rounded'}),
            'apellidos_cliente': forms.TextInput(attrs={'class': 'w-full rounded'}),
            'razon_social': forms.TextInput(attrs={'class': 'w-full rounded'}),
            'documento_cliente': forms.TextInput(attrs={'class': 'w-full rounded'}),
        }
