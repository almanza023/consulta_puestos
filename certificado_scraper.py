import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import requests
from PIL import Image
import numpy as np
import cv2
import easyocr
import PyPDF2
import pdfplumber
import re

class CertificadoVigenciaScraperAuto:
    """Scraper automatizado para certificados de vigencia de cédula"""
    
    def __init__(self, headless=True):
        """
        Inicializa el scraper de certificados de vigencia
        
        Args:
            headless (bool): Si ejecutar el navegador en modo headless
        """
        self.headless = False
        self.driver = None
        self.wait = None
        self.setup_driver()
        self.setup_directories()
    
    def setup_driver(self):
        """Configura el driver de Chrome"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Configurar descargas
            download_dir = os.path.abspath("certificados_pdf")
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)
            
            print("✅ Driver de Chrome configurado correctamente")
            
        except Exception as e:
            print(f"❌ Error al configurar el driver: {e}")
            raise
    
    def setup_directories(self):
        """Crea los directorios necesarios"""
        directories = ["captchas_img", "certificados_pdf", "certificado_results"]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 Directorio creado: {directory}")
    
    def parse_fecha_expedicion(self, fecha_expedicion):
        """
        Parsea la fecha de expedición y extrae día, mes y año
        
        Args:
            fecha_expedicion (str): Fecha en formato dd/mm/yyyy
        
        Returns:
            tuple: (dia, mes, año)
        """
        try:
            parts = fecha_expedicion.split('/')
            if len(parts) != 3:
                raise ValueError("Formato de fecha inválido")
            
            dia = parts[0].zfill(2)
            mes = parts[1].zfill(2)
            año = parts[2]
            
            return dia, mes, año
            
        except Exception as e:
            print(f"❌ Error al parsear fecha {fecha_expedicion}: {e}")
            raise
    
    def extract_pdf_data(self, pdf_path):
        """
        Extrae la información específica del PDF del certificado de vigencia
        
        Args:
            pdf_path (str): Ruta del archivo PDF
            
        Returns:
            dict: Diccionario con la información extraída
        """
        try:
            print(f"📄 Extrayendo información del PDF: {pdf_path}")
            
            # Inicializar el diccionario de datos
            extracted_data = {
                "cedula_ciudadania": None,
                "fecha_expedicion": None,
                "lugar_expedicion": None,
                "nombre": None,
                "estado": None
            }
            
            # Intentar con pdfplumber primero (mejor para texto estructurado)
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    
                    if text.strip():
                        extracted_data = self.parse_pdf_text(text)
                        print("✅ Texto extraído exitosamente con pdfplumber")
                    else:
                        raise Exception("No se pudo extraer texto con pdfplumber")
                        
            except Exception as e:
                print(f"⚠️ Error con pdfplumber: {e}")
                print("🔄 Intentando con PyPDF2...")
                
                # Fallback a PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                    
                    if text.strip():
                        extracted_data = self.parse_pdf_text(text)
                        print("✅ Texto extraído exitosamente con PyPDF2")
                    else:
                        raise Exception("No se pudo extraer texto del PDF")
            
            print(f"📋 Datos extraídos: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
            return extracted_data
            
        except Exception as e:
            print(f"❌ Error al extraer datos del PDF: {e}")
            return {
                "cedula_ciudadania": None,
                "fecha_expedicion": None,
                "lugar_expedicion": None,
                "nombre": None,
                "estado": None,
                "error": str(e)
            }
    
    def parse_pdf_text(self, text):
        """
        Parsea el texto extraído del PDF para encontrar la información específica
        
        Args:
            text (str): Texto completo del PDF
            
        Returns:
            dict: Diccionario con los datos parseados
        """
        try:
            # Limpiar el texto
            text = text.replace('\n', ' ').replace('\r', ' ')
            text = re.sub(r'\s+', ' ', text).strip()
            
            print(f"🔍 Texto a parsear: {text[:500]}...")  # Mostrar primeros 500 caracteres
            
            extracted_data = {
                "cedula_ciudadania": None,
                "fecha_expedicion": None,
                "lugar_expedicion": None,
                "nombre": None,
                "estado": None
            }
            
            # Patrón para Cédula de Ciudadanía
            cedula_patterns = [
                r'Cédula de Ciudadanía[:\s]*(\d{1,3}(?:\.\d{3})*\.\d{3})',
                r'C\.C[:\s]*(\d{1,3}(?:\.\d{3})*\.\d{3})',
                r'Documento[:\s]*(\d{1,3}(?:\.\d{3})*\.\d{3})',
                r'Número[:\s]*(\d{1,3}(?:\.\d{3})*\.\d{3})'
            ]
            
            for pattern in cedula_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data["cedula_ciudadania"] = match.group(1)
                    break
            
            # Patrón para Fecha de Expedición
            fecha_patterns = [
                r'Fecha de Expedición[:\s]*(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})',
                r'Expedición[:\s]*(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})',
                r'Fecha[:\s]*(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})'
            ]
            
            for pattern in fecha_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data["fecha_expedicion"] = match.group(1).strip()
                    break
            
            # Patrón mejorado para Lugar de Expedición (evitar capturar "A nombre de")
            lugar_patterns = [
                r'Lugar de Expedición[:\s]*([A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+?)(?:\s+A nombre de|\s+Nombre|\s+Estado|$)',
                r'Expedición[:\s]*([A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+?)(?:\s+A nombre de|\s+Nombre|\s+Estado|$)',
                r'Lugar[:\s]*([A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+?)(?:\s+A nombre de|\s+Nombre|\s+Estado|$)'
            ]
            
            for pattern in lugar_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    lugar = match.group(1).strip()
                    # Limpiar cualquier texto residual
                    lugar = re.sub(r'\s+A nombre de.*$', '', lugar, flags=re.IGNORECASE)
                    extracted_data["lugar_expedicion"] = lugar
                    break
            
            # Patrón para Nombre
            nombre_patterns = [
                r'A nombre de[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s+Estado|\s+Fecha|\s+Lugar|$)',
                r'Nombre[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s+Estado|\s+Fecha|\s+Lugar|$)',
                r'Titular[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s+Estado|\s+Fecha|\s+Lugar|$)'
            ]
            
            for pattern in nombre_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    nombre = match.group(1).strip()
                    # Limpiar el nombre de caracteres no deseados
                    nombre = re.sub(r'\s+', ' ', nombre)
                    extracted_data["nombre"] = nombre
                    break
            
            # Patrón para Estado
            estado_patterns = [
                r'Estado[:\s]*(VIGENTE|NO VIGENTE|VENCIDA?|ACTIVA?)',
                r'Vigencia[:\s]*(VIGENTE|NO VIGENTE|VENCIDA?|ACTIVA?)',
                r'Status[:\s]*(VIGENTE|NO VIGENTE|VENCIDA?|ACTIVA?)'
            ]
            
            for pattern in estado_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data["estado"] = match.group(1).upper()
                    break
            
            # Validar que se hayan extraído los datos principales
            missing_fields = [k for k, v in extracted_data.items() if v is None]
            if missing_fields:
                print(f"⚠️ Campos no encontrados: {missing_fields}")
            
            return extracted_data
            
        except Exception as e:
            print(f"❌ Error al parsear texto del PDF: {e}")
            return {
                "cedula_ciudadania": None,
                "fecha_expedicion": None,
                "lugar_expedicion": None,
                "nombre": None,
                "estado": None,
                "error": str(e)
            }
    
    def check_captcha_error(self):
        """
        Verifica si hay un error de validación del captcha
        
        Returns:
            bool: True si hay error, False si no hay error
        """
        try:
            error_span = self.driver.find_element(By.NAME, "ContentPlaceHolder1_RequiredFieldValidator2")
            error_text = error_span.text.strip()
            if error_text:
                print(f"⚠️ Error de validación detectado: {error_text}")
                return True
            else:
                return False
        except NoSuchElementException:
            return False
        except Exception as e:
            print(f"❌ Error al verificar validación del captcha: {e}")
            return False
    
    def change_captcha(self):
        """
        Hace clic en la imagen para cambiar el captcha
        
        Returns:
            bool: True si se cambió exitosamente, False si no
        """
        try:
            change_img = self.driver.find_element(By.CSS_SELECTOR, 'img[alt="Change the code"]')
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", change_img)
            time.sleep(0.5)
            change_img.click()
            print("🔄 Captcha cambiado exitosamente")
            time.sleep(2)
            return True
        except NoSuchElementException:
            print("❌ No se encontró la imagen para cambiar el captcha")
            return False
        except Exception as e:
            print(f"❌ Error al cambiar el captcha: {e}")
            return False
    
    def download_captcha_image(self, nuip):
        """
        Descarga la imagen del captcha usando el ID específico
        
        Args:
            nuip (str): NUIP para nombrar el archivo
        
        Returns:
            str: Ruta del archivo de imagen guardado
        """
        try:
            captcha_img = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="datos_contentplaceholder1_captcha1_CaptchaImage"]'))
            )
            img_src = captcha_img.get_attribute("src")
            print(f"🔍 URL del captcha: {img_src}")
            if not img_src or img_src == "":
                raise Exception("La URL del captcha está vacía")
            response = requests.get(img_src)
            if response.status_code == 200:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"captchas_img/captcha_{timestamp}.png"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    print(f"✅ Captcha descargado exitosamente: {filename} ({os.path.getsize(filename)} bytes)")
                    return filename
                else:
                    raise Exception("La imagen descargada está vacía o corrupta")
            else:
                raise Exception(f"Error HTTP al descargar captcha: {response.status_code}")
        except Exception as e:
            print(f"❌ Error al descargar captcha: {e}")
            raise
    
    def solve_captcha_with_ocr(self, image_path):
        """
        Intenta resolver el captcha usando EasyOCR con preprocesamiento específico
        
        Args:
            image_path (str): Ruta de la imagen del captcha
        
        Returns:
            str: Texto extraído del captcha
        """
        try:
            img = cv2.imread(image_path)
            print(f"🔍 Procesando imagen del captcha: {image_path}")
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, imagen_umbral = cv2.threshold(gray_img, 150, 255, cv2.THRESH_BINARY_INV)
            imagen_blanca = np.ones_like(img) * 255
            resultado = cv2.bitwise_and(img, img, mask=imagen_umbral)
            imagen_final = cv2.add(imagen_blanca, resultado, mask=cv2.bitwise_not(imagen_umbral))
            alpha = 4.0
            imagen_contraste = cv2.convertScaleAbs(imagen_final, alpha=alpha, beta=0)
            beta = 150
            imagen_brillo = cv2.convertScaleAbs(imagen_contraste, alpha=1.0, beta=beta)
            processed_path = image_path.replace('.png', '_processed.jpg')
            cv2.imwrite(processed_path, imagen_brillo)
            print(f"✅ Imagen procesada guardada: {processed_path}")
            reader = easyocr.Reader(['es'], gpu=False)
            result = reader.readtext(processed_path)
            captcha_result = ""
            best_confidence = 0
            print(f"🔍 EasyOCR encontró {len(result)} detecciones:")
            for detection in result:
                bbox, text, confidence = detection
                print(f"  📝 Texto: '{text}' | Confianza: {confidence:.2f}")
                if confidence > best_confidence:
                    captcha_result = text
                    best_confidence = confidence
            cleaned_result = self.clean_captcha_text(captcha_result)
            print(f"✅ Resultado final del captcha: Result'{captcha_result}' | Confianza: {best_confidence:.2f}")
            print(f"✅ Resultado final del captcha: '{cleaned_result}' | Confianza: {best_confidence:.2f}")
            return cleaned_result
        except Exception as e:
            print(f"❌ Error en OCR: {e}")
            return ""
    
    def clean_captcha_text(self, text):
        if not text:
            return ""
        cleaned = ''.join(text.split())
        valid_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        cleaned = ''.join(char for char in cleaned if char in valid_chars)
        return cleaned
    
    def solve_captcha_with_retry(self, nuip, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                print(f"🔄 Intento {attempt + 1} de {max_attempts} para resolver captcha")
                captcha_image_path = self.download_captcha_image(nuip)
                captcha_text = self.solve_captcha_with_ocr(captcha_image_path)
                if captcha_text and len(captcha_text) >= 3:
                    print(f"✅ Captcha resuelto en intento {attempt + 1}: '{captcha_text}'")
                    return captcha_text
                else:
                    print(f"⚠️ Captcha no resuelto en intento {attempt + 1}")
                    if attempt < max_attempts - 1:
                        if self.change_captcha():
                            time.sleep(2)
                        else:
                            print("❌ No se pudo cambiar el captcha")
            except Exception as e:
                print(f"❌ Error en intento {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    if self.change_captcha():
                        time.sleep(2)
        print(f"❌ No se pudo resolver el captcha después de {max_attempts} intentos")
        return ""
    
    def safe_click(self, element):
        """
        Hace scroll al elemento y hace clic con JavaScript para evitar errores de click intercepted
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", element)
        except Exception as e:
            print(f"❌ Error al hacer clic seguro: {e}")
            raise
    
    def scrape_certificado_vigencia(self, nuip, fecha_expedicion):
        start_time = time.time()
        try:
            print(f"🔍 Obteniendo certificado de vigencia para NUIP: {nuip}, Fecha: {fecha_expedicion}")
            dia, mes, año = self.parse_fecha_expedicion(fecha_expedicion)
            url = "https://certvigenciacedula.registraduria.gov.co/Datos.aspx"
            self.driver.get(url)
            time.sleep(3)
            
            # Guardar imagen del captcha y resolverlo por OCR
            captcha_image = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="datos_contentplaceholder1_captcha1_CaptchaImage"]')))
            captcha_image_path = self.download_captcha_image(captcha_image)
            captcha_text = self.solve_captcha_with_ocr(captcha_image_path)
            print(f"✅ Captcha resuelto: {captcha_text}")  
            
            nuip_field = self.wait.until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$TextBox1")))
            nuip_field.clear()
            nuip_field.send_keys(nuip)
            print(f"✅ NUIP ingresado: {nuip}")
            
            dia_dropdown = self.wait.until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$DropDownList1")))
            Select(dia_dropdown).select_by_value(dia)
            print(f"✅ Día seleccionado: {dia}")
            
            mes_dropdown = self.wait.until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$DropDownList2")))
            Select(mes_dropdown).select_by_value(mes)
            print(f"✅ Mes seleccionado: {mes}")
            
            año_dropdown = self.wait.until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$DropDownList3")))
            Select(año_dropdown).select_by_value(año)
            print(f"✅ Año seleccionado: {año}")
            
                      
            
            captcha_field = self.wait.until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$TextBox2")))
            
            captcha_field.clear()
            captcha_field.send_keys(captcha_text)
            
            consultar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_Button1")))
            time.sleep(1)
            self.safe_click(consultar_btn)
            print("✅ Botón 'Continuar' presionado")
            time.sleep(3)
            
            if self.check_captcha_error():
                print("🔄 Error de captcha detectado, intentando con nuevo captcha...")
                if self.change_captcha():
                    new_captcha_text = self.solve_captcha_with_retry(nuip, max_attempts=2)
                    if new_captcha_text:
                        captcha_field = self.wait.until(EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder1$TextBox2")))
                        captcha_field.clear()
                        captcha_field.send_keys(new_captcha_text)
                        print(f"✅ Nuevo captcha ingresado: {new_captcha_text}")
                        consultar_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_Button1")))
                        self.safe_click(consultar_btn)
                        print("✅ Botón 'Continuar' presionado nuevamente")
                        captcha_text = new_captcha_text
                    else:
                        raise Exception("No se pudo resolver el nuevo captcha")
                else:
                    raise Exception("No se pudo cambiar el captcha")
            
            time.sleep(5)
            current_url = self.driver.current_url
            if "Respuesta.aspx" not in current_url:
                raise Exception("No se pudo acceder a la página de respuesta")
            print("✅ Página de respuesta cargada")
            
            download_btn = self.wait.until(EC.element_to_be_clickable((By.NAME, "ctl00$ContentPlaceHolder1$Button1")))
            self.safe_click(download_btn)
            print("✅ Descarga de PDF iniciada")
            time.sleep(10)
            
            pdf_filename = self.rename_downloaded_pdf(nuip)
            
            # Extraer datos del PDF descargado
            pdf_data = None
            if pdf_filename:
                pdf_path = os.path.join("certificados_pdf", pdf_filename)
                pdf_data = self.extract_pdf_data(pdf_path)
            
            execution_time = time.time() - start_time
            
            # Estructura del JSON de respuesta con los datos solicitados
            result = {
                "status": "success",
                "message": "Certificado de vigencia obtenido exitosamente",
                "nuip": nuip,
                "fecha_expedicion": fecha_expedicion,
                "pdf_file": pdf_filename,
                "captcha_text": captcha_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_time_seconds": round(execution_time, 2),
                # Datos extraídos del PDF en el formato solicitado
                "cedula_ciudadania": pdf_data.get("cedula_ciudadania") if pdf_data else None,
                "fecha_expedicion_pdf": pdf_data.get("fecha_expedicion") if pdf_data else None,
                "lugar_expedicion": pdf_data.get("lugar_expedicion") if pdf_data else None,
                "nombre": pdf_data.get("nombre") if pdf_data else None,
                "estado": pdf_data.get("estado") if pdf_data else None,
                # Mantener también el objeto pdf_data completo para compatibilidad
                "pdf_data": pdf_data
            }
            
            print(f"✅ Certificado obtenido exitosamente: {pdf_filename}")
            print(f"📋 Datos extraídos:")
            print(f"   - Cédula: {result['cedula_ciudadania']}")
            print(f"   - Fecha Expedición: {result['fecha_expedicion_pdf']}")
            print(f"   - Lugar: {result['lugar_expedicion']}")
            print(f"   - Nombre: {result['nombre']}")
            print(f"   - Estado: {result['estado']}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = {
                "status": "error",
                "message": f"Error al obtener certificado: {str(e)}",
                "nuip": nuip,
                "fecha_expedicion": fecha_expedicion,
                "pdf_file": None,
                "captcha_text": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_time_seconds": round(execution_time, 2),
                # Campos de datos del PDF como null en caso de error
                "cedula_ciudadania": None,
                "fecha_expedicion_pdf": None,
                "lugar_expedicion": None,
                "nombre": None,
                "estado": None,
                "pdf_data": None
            }
            print(f"❌ Error al obtener certificado para NUIP {nuip}: {e}")
            return result
    
    def rename_downloaded_pdf(self, nuip):
        try:
            download_dir = "certificados_pdf"
            pdf_files = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
            if pdf_files:
                latest_file = max(pdf_files, key=lambda x: os.path.getctime(os.path.join(download_dir, x)))
                old_path = os.path.join(download_dir, latest_file)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"certificado_vigencia_{nuip}_{timestamp}.pdf"
                new_path = os.path.join(download_dir, new_filename)
                os.rename(old_path, new_path)
                print(f"✅ PDF renombrado: {new_filename}")
                return new_filename
            else:
                raise Exception("No se encontró archivo PDF descargado")
        except Exception as e:
            print(f"❌ Error al renombrar PDF: {e}")
            return None
    
    def close(self):
        if self.driver:
            self.driver.quit()
            print("🔒 Driver cerrado correctamente")
            
 
    def scrape_multiple_certificados(self, queries_list, delay=5):
        """
        Procesa múltiples consultas de certificados de vigencia
        
        Args:
            queries_list (list): Lista de diccionarios con 'nuip' y 'fecha_expedicion'
            delay (int): Delay entre consultas en segundos
            
        Returns:
            list: Lista de resultados
        """
        results = []
        total = len(queries_list)
        
        for i, query in enumerate(queries_list):
            print(f"🔄 Procesando certificado {i+1}/{total}: NUIP {query['nuip']}")
            
            try:
                result = self.scrape_certificado_vigencia(query['nuip'], query['fecha_expedicion'])
                results.append(result)
                
                # Delay entre consultas si no es la última
                if i < total - 1:
                    print(f"⏳ Esperando {delay} segundos antes de la siguiente consulta...")
                    time.sleep(delay)
                    
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"Error al procesar NUIP {query['nuip']}: {str(e)}",
                    "nuip": query['nuip'],
                    "fecha_expedicion": query['fecha_expedicion'],
                    "pdf_file": None,
                    "cedula_ciudadania": None,
                    "fecha_expedicion_pdf": None,
                    "lugar_expedicion": None,
                    "nombre": None,
                    "estado": None,
                    "pdf_data": None,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "execution_time_seconds": 0.0
                }
                results.append(error_result)
                print(f"❌ Error en consulta {i+1}: {e}")
        
        return results



def save_certificado_results(result, filename=None):
    try:
        results_dir = "certificado_results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"certificado_query_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Resultados guardados en: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error al guardar resultados: {e}")
        return None


def test_certificado_scraper():
    scraper = CertificadoVigenciaScraperAuto(headless=False)
    try:
        result = scraper.scrape_certificado_vigencia("1102877148", "15/03/1990")
        print("Resultado de la prueba:", json.dumps(result, indent=2, ensure_ascii=False))
        save_certificado_results(result)
    finally:
        scraper.close()


if __name__ == "__main__":
    test_certificado_scraper()