from django.urls import path
from .views import admin_dashboard, gestion_usuarios
urlpatterns = [
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('usuarios/', gestion_usuarios, name='gestion_usuarios'),
]
