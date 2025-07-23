from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

# Configura opciones para Chrome
options = Options()
options.headless = False  # Cambia a True si no deseas abrir la ventana del navegador

# Ruta del WebDriver
# Ruta correcta a ChromeDriver
driver_path = "C:/Users/rodri/Downloads/chromedriver-win64/chromedriver.exe"

# Configura el WebDriver con la ruta correcta
driver = webdriver.Chrome(service=Service(driver_path), options=options)


# Abre la página de login
driver.get("http://127.0.0.1:8000/login/")  # Cambia a la URL de tu página

# Espera para que la página cargue completamente
time.sleep(2)

# Interactúa con los elementos
username = driver.find_element(By.NAME, "username")
password = driver.find_element(By.NAME, "password")
login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')

# Ingresa credenciales
username.send_keys("usuario_test")
password.send_keys("password_test")

# Haz clic en el botón de login
login_button.click()

# Espera para ver el resultado
time.sleep(2)

# Realiza más interacciones o verificaciones aquí

# Cierra el navegador
driver.quit()
