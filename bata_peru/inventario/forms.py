from django import forms
from .models import Producto, Categoria, Subcategoria  # 👈 asegúrate de importar

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre',
            'marca',
            'color',
            'categoria',
            'subcategoria',
            'precio',
            'cantidad',
            'imagen',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),
            'marca': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),
            'color': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),
            'categoria': forms.Select(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),     # ✅
            'subcategoria': forms.Select(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),  # ✅
            'precio': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),
            'cantidad': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'w-full border-gray-300 rounded shadow-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.all()
        self.fields['subcategoria'].queryset = Subcategoria.objects.all()
