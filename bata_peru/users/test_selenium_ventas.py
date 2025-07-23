from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pytest

@pytest.fixture(scope='module')
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

# Prueba E2E: login como usuario de ventas y acceso a módulos de ventas
@pytest.mark.parametrize('username,password', [
    ('adminuser', 'adminpass'),
    ('cajerouser', 'cajeropass'),
    ('inventariouser', 'inventariopass'),
])
def test_login_and_ventas_access(driver, live_server, username, password):
    driver.get(live_server.url + '/login/')
    time.sleep(1)
    driver.find_element(By.ID, 'username').send_keys(username)
    driver.find_element(By.ID, 'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    # Acceso a catálogo de ventas
    driver.get(live_server.url + '/ventas/catalogo/')
    time.sleep(1)
    assert 'Catálogo' in driver.page_source
    # Acceso a historial de ventas
    driver.get(live_server.url + '/ventas/historial/')
    time.sleep(1)
    assert 'Historial de Ventas' in driver.page_source
    # Acceso a estadísticas de ventas
    driver.get(live_server.url + '/ventas/estadisticas/')
    time.sleep(1)
    assert 'Estadísticas' in driver.page_source

# Prueba E2E: apertura de caja, compra y cierre de caja
@pytest.mark.django_db
def test_apertura_compra_cierre(driver, live_server):
    # Login como empleado
    driver.get(live_server.url + '/login/')
    driver.find_element(By.ID, 'username').send_keys('empleadoventas')
    driver.find_element(By.ID, 'password').send_keys('empleadopass')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    # Apertura de caja
    driver.get(live_server.url + '/ventas/apertura_caja/')
    driver.find_element(By.ID, 'monto_inicial').send_keys('1000')
    driver.find_element(By.ID, 'comentario').send_keys('Apertura de caja para pruebas')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    assert 'Solicitud de apertura enviada' in driver.page_source or 'pendiente' in driver.page_source
    # Simular agregar producto al carrito (esto depende de tu lógica, aquí ejemplo por URL)
    driver.get(live_server.url + '/ventas/agregar_carrito/1/')  # Agrega producto con id=1
    time.sleep(1)
    # Realizar compra
    driver.get(live_server.url + '/ventas/realizar_compra/')
    driver.find_element(By.ID, 'tipo_pago').send_keys('efectivo')
    driver.find_element(By.ID, 'tipo_documento').send_keys('dni')
    driver.find_element(By.ID, 'documento_cliente').send_keys('12345678')
    driver.find_element(By.ID, 'nombres_cliente').send_keys('Juan')
    driver.find_element(By.ID, 'apellidos_cliente').send_keys('Pérez')
    driver.find_element(By.ID, 'monto_pagado').send_keys('100')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    assert 'Venta registrada correctamente' in driver.page_source
    # Cierre de caja
    driver.get(live_server.url + '/ventas/cierre_caja/')
    driver.find_element(By.ID, 'comentario').send_keys('Cierre de caja de prueba')
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)
    assert 'Solicitud de cierre enviada' in driver.page_source or 'pendiente' in driver.page_source
