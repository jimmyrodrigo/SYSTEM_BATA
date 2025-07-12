from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import pytest

# Configuración básica para Selenium
@pytest.fixture(scope='module')
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Ejecuta sin abrir ventana
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

# Prueba E2E: login y acceso por rol
@pytest.mark.parametrize('username,password,expected_url', [
    ('adminuser', 'adminpass', '/dashboard/admin/'),
    ('cajerouser', 'cajeropass', '/dashboard/cajero/'),
    ('inventariouser', 'inventariopass', '/dashboard/inventario/'),
])
def test_login_roles(driver, live_server, username, password, expected_url):
    driver.get(live_server.url + '/login/')
    time.sleep(1)
    driver.find_element(By.ID, 'username').send_keys(username)
    driver.find_element(By.ID, 'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    assert expected_url in driver.current_url

# Prueba E2E: acceso a compras/ventas
@pytest.mark.parametrize('url,element_text', [
    ('/ventas/catalogo/', 'Catálogo'),
    ('/ventas/historial/', 'Historial de Ventas'),
    ('/ventas/estadisticas/', 'Estadísticas'),
])
def test_acceso_modulos(driver, live_server, url, element_text):
    # Login como usuario válido
    driver.get(live_server.url + '/login/')
    driver.find_element(By.ID, 'username').send_keys('adminuser')
    driver.find_element(By.ID, 'password').send_keys('adminpass')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    # Acceder al módulo
    driver.get(live_server.url + url)
    time.sleep(1)
    assert element_text in driver.page_source
