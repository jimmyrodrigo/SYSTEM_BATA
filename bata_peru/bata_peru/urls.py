from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Redirige / directamente a login si no hay sesión
    path('', RedirectView.as_view(url='/login/')),

    # Autenticación personalizada (login, registro, logout)
    path('', include('bata_peru.users.auth_urls')),

    # Dashboards por rol
    path('usuarios/', include('bata_peru.users.dashboard_urls')),  # Admin dashboard
    path('ventas/', include('bata_peru.ventas.urls')),             # Módulo ventas
    path('inventario/', include('bata_peru.inventario.urls')),     # Módulo inventario
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
