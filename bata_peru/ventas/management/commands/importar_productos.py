import csv
import random
from datetime import datetime, timedelta
from django.core.files import File
from django.core.management.base import BaseCommand
from inventario.models import Producto, Categoria, Subcategoria
from pathlib import Path

class Command(BaseCommand):
    help = 'Importa productos desde un archivo CSV con cantidad incluida, fecha de ingreso aleatoria y talla'

    def handle(self, *args, **kwargs):
        path_csv = 'catalogo_bata_completo.csv'  # Ruta del archivo CSV

        with open(path_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                imagen_path = Path('media/' + row['imagen'].strip())
                if not imagen_path.exists():
                    self.stdout.write(self.style.ERROR(f"❌ No se encontró la imagen: {imagen_path}"))
                    continue

                # Obtener o crear la categoría
                categoria_nombre = row['categoria'].strip()
                categoria_obj, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)

                # Obtener o crear la subcategoría asociada a la categoría
                subcategoria_nombre = row['subcategoria'].strip()
                subcategoria_obj, _ = Subcategoria.objects.get_or_create(
                    nombre=subcategoria_nombre,
                    categoria=categoria_obj
                )

                # Generar fecha aleatoria entre 10 y 20 de abril de 2025
                fecha_random = datetime(2025, 4, 10) + timedelta(days=random.randint(0, 10))

                # Leer talla directamente del CSV (puede ser '' o None)
                talla = row.get('talla', '').strip() or None

                # Crear o actualizar el producto
                producto, creado = Producto.objects.update_or_create(
                    nombre=row['nombre'].strip(),
                    defaults={
                        'marca': row['marca'].strip(),
                        'color': row['color'].strip(),
                        'categoria': categoria_obj,
                        'subcategoria': subcategoria_obj,
                        'precio': row['precio'],
                        'cantidad': int(row['cantidad']),
                        'fecha_ingreso': fecha_random,
                        'talla': talla,
                    }
                )

                # Asignar imagen si es nuevo
                if creado:
                    with open(imagen_path, 'rb') as img_file:
                        producto.imagen.save(imagen_path.name, File(img_file), save=True)

                mensaje = "✅ Agregado" if creado else "🔄 Actualizado"
                self.stdout.write(self.style.SUCCESS(f"{mensaje}: {producto.nombre} | ID {producto.id} | Fecha {producto.fecha_ingreso.strftime('%Y-%m-%d')} | Talla: {producto.talla}"))
