import logging
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

# Configurar el logger para imprimir detalles en la terminal
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class LoginTest(TestCase):

    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(username='adminuser', password='password123', rol='admin')
        self.empleado_user = get_user_model().objects.create_user(username='empleadouser', password='password123', rol='empleado')
        self.inventario_user = get_user_model().objects.create_user(username='inventariouser', password='password123', rol='inventario')

    def test_login_redirect_admin(self):
        response = self.client.post(reverse('login'), {'username': 'adminuser', 'password': 'password123'})
        self.assertEqual(response.status_code, 302)
        logger.debug(f"Admin user redirected to: {response.url}")
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_login_redirect_empleado(self):
        response = self.client.post(reverse('login'), {'username': 'empleadouser', 'password': 'password123'})
        self.assertEqual(response.status_code, 302)
        logger.debug(f"Empleado user redirected to: {response.url}")
        self.assertRedirects(response, reverse('ventas_dashboard'))

    def test_login_redirect_inventario(self):
        response = self.client.post(reverse('login'), {'username': 'inventariouser', 'password': 'password123'})
        self.assertEqual(response.status_code, 302)
        logger.debug(f"Inventario user redirected to: {response.url}")
        self.assertRedirects(response, reverse('catalogo_inventario'))

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {'username': 'wronguser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 400) 
        logger.debug(f"Invalid credentials response: {response.status_code}")
