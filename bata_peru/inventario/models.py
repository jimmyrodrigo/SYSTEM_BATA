from django.db import models

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Subcategoria(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"

class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    imagen = models.ImageField(upload_to='productos/')
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    stock_minimo = models.IntegerField(default=1)
    fecha_ingreso = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nombre
