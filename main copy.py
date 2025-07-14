import requests
import time
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Import the official 2captcha library
from twocaptcha import TwoCaptcha

class TwoCaptchaSolver:
    def __init__(self, api_key):
        self.api_key = api_key
        self.solver = TwoCaptcha(api_key)
    
    def get_balance(self):
        """Obtiene el balance de la cuenta"""
        try:
            balance = self.solver.balance()
            return f"Balance: ${balance} USD"
        except Exception as e:
            return f"Error al obtener balance: {e}"
    
    def solve_recaptcha_v2(self, site_key, page_url, invisible=False):
        """
        Resuelve reCAPTCHA v2 usando la librería oficial de 2captcha
        
        Args:
            site_key (str): Site key del reCAPTCHA
            page_url (str): URL de la página donde está el reCAPTCHA
            invisible (bool): True para invisible reCAPTCHA, False para normal
        
        Returns:
            str: Token de respuesta del reCAPTCHA
        """
        print("Enviando reCAPTCHA a 2captcha para resolver...")
        print(f"🔍 Debugging - Site key: {site_key}")
        print(f"🔍 Debugging - URL: {page_url}")
        print(f"🔍 Debugging - Invisible: {invisible}")
        
        try:
            # Resolver reCAPTCHA usando la librería oficial
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url,
                invisible=1 if invisible else 0
            )
            
            print("✅ reCAPTCHA resuelto exitosamente!")
            print(f"🔍 Debugging - Respuesta: {result}")
            return result['code']
            
        except Exception as e:
            print(f"🔍 Debugging - Error completo: {str(e)}")
            print(f"🔍 Debugging - Tipo de error: {type(e)}")
            raise Exception(f"Error al resolver reCAPTCHA: {e}")

class RegistraduriaScraperAuto:
    def __init__(self, captcha_api_key, headless=False, extension_path=None):
        self.captcha_solver = TwoCaptchaSolver(captcha_api_key)
        self.driver = None
        self.extension_path = extension_path
        self.setup_driver(headless)
        
        # Verificar balance
        balance = self.captcha_solver.get_balance()
        print(f"2captcha {balance}")
    
    def setup_driver(self, headless=False):
        """Configura el driver de Chrome con soporte para extensiones"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless")
        
        # Configuraciones para evitar detección
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Cargar extensión si se proporciona la ruta
        if self.extension_path:
            if os.path.exists(self.extension_path):
                chrome_options.add_argument(f"--load-extension={self.extension_path}")
                print(f"🔌 Cargando extensión desde: {self.extension_path}")
            else:
                print(f"⚠️ Advertencia: No se encontró la extensión en: {self.extension_path}")
        
        # Permitir extensiones en modo incógnito (opcional)
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-web-security")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Ejecutar script para ocultar webdriver
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Si hay extensión cargada, esperar un momento para que se inicialice
        if self.extension_path:
            print("⏳ Esperando que la extensión se inicialice...")
            time.sleep(3)
    
    def load_page(self):
        """Carga la página de consulta"""
        try:
            print("Cargando página de la Registraduría...")
            self.driver.get("https://wsp.registraduria.gov.co/censo/consultar/")
            
            # Esperar a que el formulario se cargue
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "nuip"))
            )
            
            # Esperar un poco más para que todo se cargue completamente
            time.sleep(3)
            
            print("✅ Página cargada correctamente")
            return True
        
        except TimeoutException:
            print("❌ Error: Tiempo de espera agotado al cargar la página")
            return False
        except Exception as e:
            print(f"❌ Error al cargar la página: {e}")
            return False
    
    def fill_form(self, nuip):
        """Llena el formulario con los datos"""
        try:
            print(f"Llenando formulario para NUIP: {nuip}")
            
            # Llenar campo de identificación
            nuip_field = self.driver.find_element(By.ID, "nuip")
            nuip_field.clear()
            nuip_field.send_keys(str(nuip))
            
            # Esperar a que se carguen las opciones del select
            time.sleep(2)
            
            # Seleccionar tipo de elección
            select_element = Select(self.driver.find_element(By.ID, "tipo"))
            
            # Buscar la primera opción válida (que no sea -1)
            options = select_element.options
            selected = False
            
            for option in options:
                value = option.get_attribute("value")
                if value and value != "-1":
                    select_element.select_by_value(value)
                    print(f"Seleccionado tipo de elección: {option.text}")
                    selected = True
                    break
            
            if not selected:
                print("⚠️ Advertencia: No se pudo seleccionar tipo de elección")
            
            print("✅ Formulario llenado correctamente")
            return True
        
        except NoSuchElementException as e:
            print(f"❌ Error: Elemento no encontrado - {e}")
            return False
        except Exception as e:
            print(f"❌ Error al llenar formulario: {e}")
            return False
    
    def get_recaptcha_site_key(self):
        """Extrae dinámicamente el site key del reCAPTCHA desde la página"""
        try:
            # Buscar el site key en el elemento div del reCAPTCHA
            recaptcha_element = self.driver.find_element(By.CLASS_NAME, "g-recaptcha")
            site_key = recaptcha_element.get_attribute("data-sitekey")
            
            if site_key:
                print(f"🔍 Site key encontrado dinámicamente: {site_key}")
                return site_key
            else:
                print("⚠️ No se pudo extraer el site key dinámicamente, usando el hardcodeado")
                return "6LcthjAgAAAAFIQLxy52074zanHv47cIvmIHglH"
                
        except NoSuchElementException:
            print("⚠️ Elemento reCAPTCHA no encontrado, usando site key hardcodeado")
            return "6LcthjAgAAAAFIQLxy52074zanHv47cIvmIHglH"
        except Exception as e:
            print(f"⚠️ Error al extraer site key: {e}, usando hardcodeado")
            return "6LcthjAgAAAAFIQLxy52074zanHv47cIvmIHglH"
    
    def solve_recaptcha(self):
        """Resuelve el reCAPTCHA automáticamente usando la librería oficial"""
        try:
            # Obtener site key dinámicamente
            site_key = self.get_recaptcha_site_key()
            page_url = self.driver.current_url
            
            print(f"🤖 Resolviendo reCAPTCHA automáticamente con 2captcha...")
            print(f"Site key: {site_key}")
            print(f"URL: {page_url}")
            
            # Verificar que el reCAPTCHA esté presente en la página
            try:
                recaptcha_frame = self.driver.find_element(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                print("✅ reCAPTCHA iframe encontrado en la página")
            except NoSuchElementException:
                print("⚠️ No se encontró iframe de reCAPTCHA, continuando...")
            
            # Resolver reCAPTCHA usando la librería oficial
            captcha_response = self.captcha_solver.solve_recaptcha_v2(site_key, page_url, invisible=False)
            
            # Inyectar la respuesta en la página
            injection_script = f"""
                console.log('🔍 Iniciando inyección de reCAPTCHA...');
                
                // Buscar el textarea de respuesta del reCAPTCHA
                var responseElement = document.getElementById('g-recaptcha-response');
                if (!responseElement) {{
                    responseElement = document.querySelector('[name="g-recaptcha-response"]');
                }}
                
                if (responseElement) {{
                    console.log('✅ Elemento g-recaptcha-response encontrado');
                    responseElement.innerHTML = '{captcha_response}';
                    responseElement.value = '{captcha_response}';
                    responseElement.style.display = 'block';
                    console.log('✅ Respuesta inyectada en textarea');
                }} else {{
                    console.log('❌ No se encontró elemento g-recaptcha-response');
                }}
                
                // Sobrescribir la función grecaptcha.getResponse
                if (typeof grecaptcha !== 'undefined') {{
                    console.log('✅ grecaptcha disponible, sobrescribiendo getResponse');
                    grecaptcha.getResponse = function() {{ 
                        console.log('✅ grecaptcha.getResponse llamado, retornando: {captcha_response}');
                        return '{captcha_response}'; 
                    }};
                }} else {{
                    console.log('⚠️ grecaptcha no está disponible');
                }}
                
                // Disparar eventos para notificar que el reCAPTCHA fue resuelto
                var recaptchaElements = document.querySelectorAll('.g-recaptcha');
                console.log('🔍 Elementos .g-recaptcha encontrados:', recaptchaElements.length);
                
                recaptchaElements.forEach(function(element, index) {{
                    console.log('🔍 Procesando elemento reCAPTCHA', index);
                    
                    // Disparar evento change
                    var changeEvent = new Event('change', {{ bubbles: true }});
                    element.dispatchEvent(changeEvent);
                    
                    // Si tiene callback, ejecutarlo
                    if (element.callback && typeof element.callback === 'function') {{
                        console.log('✅ Ejecutando callback del elemento', index);
                        element.callback('{captcha_response}');
                    }}
                }});
                
                console.log('✅ Inyección de reCAPTCHA completada');
                return 'success';
            """
            
            result = self.driver.execute_script(injection_script)
            print(f"🔍 Resultado de inyección: {result}")
            
            # Esperar un momento para que se procese
            time.sleep(3)
            
            # Verificar que la respuesta se haya inyectado correctamente
            verification_script = """
                var responseElement = document.getElementById('g-recaptcha-response') || 
                                    document.querySelector('[name="g-recaptcha-response"]');
                if (responseElement && responseElement.value) {
                    return {
                        success: true,
                        response_length: responseElement.value.length,
                        response_preview: responseElement.value.substring(0, 50) + '...'
                    };
                } else {
                    return {
                        success: false,
                        message: 'No se encontró respuesta en el elemento'
                    };
                }
            """
            
            verification_result = self.driver.execute_script(verification_script)
            print(f"🔍 Verificación de inyección: {verification_result}")
            
            if verification_result.get('success'):
                print("✅ reCAPTCHA resuelto e inyectado correctamente en la página")
                return True
            else:
                print(f"❌ Error en la verificación: {verification_result.get('message')}")
                return False
        
        except Exception as e:
            print(f"❌ Error al resolver reCAPTCHA: {e}")
            print(f"🔍 Tipo de error: {type(e)}")
            import traceback
            print(f"🔍 Traceback completo: {traceback.format_exc()}")
            return False
    
    def submit_form(self):
        """Envía el formulario"""
        try:
            print("Enviando formulario...")
            
            # Buscar y hacer clic en el botón de enviar
            submit_button = self.driver.find_element(By.ID, "enviar")
            
            # Scroll hacia el botón para asegurar que esté visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)
            
            submit_button.click()
            
            # Esperar a que aparezcan los resultados
            print("Esperando resultados...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "consulta"))
            )
            
            print("✅ Formulario enviado y resultados obtenidos")
            return True
        
        except TimeoutException:
            print("❌ Error: No se encontraron resultados o tiempo de espera agotado")
            
            # Verificar si hay algún mensaje de error
            try:
                error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".alert, .error, .warning")
                for element in error_elements:
                    if element.is_displayed():
                        print(f"Mensaje en página: {element.text}")
            except:
                pass
            
            return False
        
        except NoSuchElementException as e:
            print(f"❌ Error: Botón de envío no encontrado - {e}")
            return False
        except Exception as e:
            print(f"❌ Error al enviar formulario: {e}")
            return False
    
    def extract_data(self):
        """Extrae los datos de la tabla de resultados"""
        try:
            print("Extrayendo datos de la tabla...")
            
            # Buscar la tabla de resultados
            table = self.driver.find_element(By.ID, "consulta")
            
            # Extraer headers
            headers = []
            header_elements = table.find_elements(By.CSS_SELECTOR, "thead th")
            for header in header_elements:
                headers.append(header.text.strip())
            
            print(f"Headers encontrados: {headers}")
            
            # Extraer datos de las filas
            rows_data = []
            row_elements = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            for row in row_elements:
                row_data = {}
                cells = row.find_elements(By.TAG_NAME, "td")
                
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        # Limpiar el texto
                        cell_text = cell.text.strip()
                        row_data[headers[i]] = cell_text
                
                if row_data:  # Solo agregar si tiene datos
                    rows_data.append(row_data)
            
            result = {
                "status": "success",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "data": rows_data,
                "total_records": len(rows_data)
            }
            
            print(f"✅ Datos extraídos: {len(rows_data)} registros")
            return result
        
        except NoSuchElementException:
            print("❌ Error: Tabla de resultados no encontrada")
            return {
                "status": "error", 
                "message": "Tabla de resultados no encontrada",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"❌ Error al extraer datos: {e}")
            return {
                "status": "error", 
                "message": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def scrape_nuip(self, nuip):
        """Proceso completo de scraping para un NUIP"""
        print(f"\n{'='*50}")
        print(f"INICIANDO CONSULTA PARA NUIP: {nuip}")
        print(f"{'='*50}")
        
        try:
            # 1. Cargar página
            if not self.load_page():
                return {"status": "error", "message": "Error al cargar la página", "nuip": nuip}
            
            # 2. Llenar formulario
            if not self.fill_form(nuip):
                return {"status": "error", "message": "Error al llenar el formulario", "nuip": nuip}
            
            # 3. Resolver reCAPTCHA
            if not self.solve_recaptcha():
                return {"status": "error", "message": "Error al resolver reCAPTCHA", "nuip": nuip}
            
            # 4. Enviar formulario
            if not self.submit_form():
                return {"status": "error", "message": "Error al enviar formulario", "nuip": nuip}
            
            # 5. Extraer datos
            result = self.extract_data()
            result["nuip"] = nuip
            
            print(f"✅ CONSULTA COMPLETADA PARA NUIP: {nuip}")
            return result
        
        except Exception as e:
            print(f"❌ Error general en consulta: {e}")
            return {
                "status": "error", 
                "message": f"Error general: {str(e)}", 
                "nuip": nuip,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def scrape_multiple_nuips(self, nuips_list, delay=5):
        """Consulta múltiples NUIPs con delay entre consultas"""
        results = []
        total = len(nuips_list)
        
        print(f"\n🚀 INICIANDO CONSULTA MASIVA DE {total} NUIPs")
        print(f"Delay entre consultas: {delay} segundos")
        
        for i, nuip in enumerate(nuips_list, 1):
            print(f"\n📋 Procesando {i}/{total}: {nuip}")
            
            result = self.scrape_nuip(nuip)
            results.append(result)
            
            # Delay entre consultas (excepto en la última)
            if i < total:
                print(f"⏳ Esperando {delay} segundos antes de la siguiente consulta...")
                time.sleep(delay)
        
        print(f"\n🎉 CONSULTA MASIVA COMPLETADA: {total} NUIPs procesados")
        return results
    
    def close(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
            print("🔒 Navegador cerrado")

# Función para guardar resultados
def save_results(data, filename=None):
    """Guarda los resultados en un archivo JSON"""
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"consulta_registraduria_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Resultados guardados en: {filename}")
    return filename

# Ejemplo de uso
if __name__ == "__main__":
    # Cargar API key desde variables de entorno
    API_KEY = os.getenv('APIKEY_2CAPTCHA')
    
    # Verificar que la API key esté disponible
    if not API_KEY:
        print("❌ Error: No se encontró la API key de 2captcha")
        print("Asegúrate de que el archivo .env contenga: APIKEY_2CAPTCHA=tu_api_key")
        sys.exit(1)
    
    print(f"🔑 API Key cargada: {API_KEY[:10]}...")  # Mostrar solo los primeros 10 caracteres
    
    # Ruta a la extensión (opcional)
    # Ejemplo: "/ruta/a/tu/extension" o None si no quieres cargar extensión
    EXTENSION_PATH = None  # Cambia esto por la ruta a tu extensión
    
    # Crear scraper con soporte para extensiones
    scraper = RegistraduriaScraperAuto(API_KEY, headless=False, extension_path=EXTENSION_PATH)
    
    try:
        # Ejemplo 1: Consultar un solo NUIP
        nuip_ejemplo = "1102877148"
        resultado = scraper.scrape_nuip(nuip_ejemplo)
        
        print(f"\n📊 RESULTADO FINAL:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        # Guardar resultado
        save_results(resultado)
        
    except KeyboardInterrupt:
        print("\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        import traceback
        print(f"🔍 Traceback completo: {traceback.format_exc()}")
    finally:
        scraper.close()