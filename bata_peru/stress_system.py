from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Función para realizar el login y medir el rendimiento
def measure_performance(driver_path, username, password):
    options = Options()
    options.headless = True  # Configura el navegador en modo headless para no abrir la ventana

    # Configura el WebDriver
    driver = webdriver.Chrome(service=Service(driver_path), options=options)

    # Mide el tiempo de inicio de sesión
    start_time = time.time()

    # Abre la página de login
    driver.get("http://127.0.0.1:8000/login/")  # Cambia la URL de acuerdo con tu página de login

    # Espera a que los campos de login estén presentes
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password")))

    # Interactúa con los campos de entrada y el botón de login
    username_field = driver.find_element(By.NAME, "username")
    password_field = driver.find_element(By.NAME, "password")
    login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')

    # Ingresa las credenciales correctas
    username_field.send_keys(username)
    password_field.send_keys(password)
    login_button.click()

    # Espera hasta que la página de inicio cargue
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "some_element_on_dashboard")))  # Ajusta según tu página

    # Mide el tiempo total de carga
    end_time = time.time()
    login_time = end_time - start_time  # Tiempo que tardó en cargar la página de inicio

    print(f"Tiempo de login: {login_time:.2f} segundos")

    # Realiza una interacción adicional en el dashboard (por ejemplo, hacer clic en un botón o navegar)
    start_time = time.time()

    # Ejemplo de interactuar con un botón en el dashboard (ajustar según tu página)
    dashboard_button = driver.find_element(By.ID, "dashboard_button")
    dashboard_button.click()

    # Espera hasta que la nueva página o interacción cargue
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "next_page_element")))

    # Mide el tiempo de la segunda interacción
    end_time = time.time()
    interaction_time = end_time - start_time  # Tiempo de interacción adicional

    print(f"Tiempo de interacción adicional: {interaction_time:.2f} segundos")

    # Calcula el rendimiento general basado en los tiempos de carga
    total_time = login_time + interaction_time
    print(f"Tiempo total de rendimiento (login + interacción): {total_time:.2f} segundos")

    # Cierra el navegador
    driver.quit()

# Configuración de la ruta del WebDriver
driver_path = "C:/Users/rodri/Downloads/chromedriver-win64/chromedriver.exe"

# Credenciales de login correctas
username = "KatulinDesparv"
password = "mimundopq"

# Realiza el test de rendimiento
measure_performance(driver_path, username, password)
