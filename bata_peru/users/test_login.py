import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_login_success(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='testpass123', token='admintoken')
    url = reverse('login')
    response = client.post(url, {'username': 'testuser', 'password': 'testpass123'})
    assert response.status_code == 302  # Redirige tras login
    assert response.url != url

@pytest.mark.django_db
def test_login_fail(client):
    url = reverse('login')
    response = client.post(url, {'username': 'wrong', 'password': 'wrong'})
    assert response.status_code == 200
    assert 'Usuario o contraseña incorrectos' in response.content.decode()

@pytest.mark.django_db
def test_token_required(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser2', password='testpass123', token='admintoken')
    url = reverse('registro')
    response = client.post(url, {
        'username': 'nuevo',
        'password': 'testpass123',
        'token': ''  # Sin token
    })
    assert response.status_code == 200
    assert 'Token de administrador es requerido' in response.content.decode()
# Prueba: campos vacíos
@pytest.mark.django_db
def test_login_empty_fields(client):
    url = reverse('login')
    response = client.post(url, {'username': '', 'password': ''})
    assert response.status_code == 200
    assert 'Este campo es obligatorio' in response.content.decode() or 'Usuario o contraseña incorrectos' in response.content.decode()

# Prueba: acceso a login estando autenticado
@pytest.mark.django_db
def test_login_redirect_authenticated(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser3', password='testpass123', token='admintoken')
    client.login(username='testuser3', password='testpass123')
    url = reverse('login')
    response = client.get(url)
    # Debe redirigir al dashboard o página principal
    assert response.status_code == 302

# Prueba: logout
@pytest.mark.django_db
def test_logout(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser4', password='testpass123', token='admintoken')
    client.login(username='testuser4', password='testpass123')
    url = reverse('logout')
    response = client.post(url)
    assert response.status_code == 302

# Prueba: login con usuario inactivo
@pytest.mark.django_db
def test_login_inactive_user(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser5', password='testpass123', token='admintoken', is_active=False)
    url = reverse('login')
    response = client.post(url, {'username': 'testuser5', 'password': 'testpass123'})
    assert response.status_code == 200
    assert 'Usuario o contraseña incorrectos' in response.content.decode()

# Para pruebas E2E con Selenium, crea test_selenium_login.py y configura el driver
# Ejemplo base:
# from selenium import webdriver
# def test_login_e2e():
#     driver = webdriver.Chrome()
#     driver.get('http://localhost:8000/login/')
#     driver.find_element_by_id('username').send_keys('testuser')
#     driver.find_element_by_id('password').send_keys('testpass123')
#     driver.find_element_by_css_selector('button[type="submit"]').click()
#     assert 'Dashboard' in driver.page_source
#     driver.quit()
