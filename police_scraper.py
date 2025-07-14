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

class PoliciaScraperAuto:
    """Scraper automatizado para consultas de nombres en el sistema de la Policía Nacional"""
    
    def __init__(self, headless=True):
        """
        Inicializa el scraper de policía
        
        Args:
            headless (bool): Si ejecutar el navegador en modo headless
        """
        self.headless = headless
        self.driver = None
        self.wait = None
        self.setup_driver()
    
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
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)  # Aumentado el timeout
            
            print("✅ Driver de Chrome configurado correctamente")
            
        except Exception as e:
            print(f"❌ Error al configurar el driver: {e}")
            raise
    
    def scrape_name_by_nuip(self, nuip, fecha_expedicion):
        """
        Consulta el nombre de una persona por NUIP y fecha de expedición
        
        Args:
            nuip (str): Número único de identificación personal
            fecha_expedicion (str): Fecha de expedición en formato dd/mm/yyyy
        
        Returns:
            dict: Resultado de la consulta
        """
        start_time = time.time()
        
        try:
            print(f"🔍 Consultando nombre para NUIP: {nuip}, Fecha: {fecha_expedicion}")
            
            # Navegar a la página de consulta de la policía
            url = "https://srvcnpc.policia.gov.co/PSC/frm_cnp_consulta.aspx"
            self.driver.get(url)
            
            # Esperar a que la página cargue completamente
            time.sleep(3)
            
            # 1. Seleccionar tipo de documento (value 55)
            tipo_doc_dropdown = self.wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder3_ddlTipoDoc"))
            )
            select_tipo_doc = Select(tipo_doc_dropdown)
            select_tipo_doc.select_by_value("55")
            print("✅ Tipo de documento seleccionado (value 55)")
            
            # Esperar un segundo
            time.sleep(1)            
            
            # 2. Llenar el campo NUIP
            nuip_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder3_txtExpediente"))
            )
            nuip_field.clear()
            nuip_field.send_keys(nuip)
            print(f"✅ NUIP ingresado: {nuip}")
            
            # 3. Llenar la fecha de expedición
            fecha_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "ctl00$ContentPlaceHolder3$txtFechaexp"))
            )
            fecha_field.clear()
            fecha_field.send_keys(fecha_expedicion)
            print(f"✅ Fecha de expedición ingresada: {fecha_expedicion}")
            
            # 4. Hacer clic en el botón de consultar
            consultar_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "ctl00_ContentPlaceHolder3_btnConsultar2"))
            )
            consultar_btn.click()
            print("✅ Botón de consultar presionado")
            
            # 5. Esperar a que aparezcan los resultados
            time.sleep(5)  # Dar tiempo para que procese la consulta
            
            # 6. Intentar encontrar el nombre en los resultados
            try:
                # Buscar el elemento que contiene el nombre
                nombre_element = self.wait.until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder3_txtNameUser"))
                )
                nombre = nombre_element.text.strip()
                
                # Remover el punto final si existe
                if nombre.endswith('.'):
                    nombre = nombre[:-1]
                
                if nombre:
                    execution_time = time.time() - start_time
                    
                    result = {
                        "status": "success",
                        "message": "Nombre encontrado exitosamente",
                        "nuip": nuip,
                        "fecha_expedicion": fecha_expedicion,
                        "name": nombre,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "execution_time_seconds": round(execution_time, 2)
                    }
                    
                    print(f"✅ Nombre encontrado: {nombre}")
                    return result
                else:
                    raise NoSuchElementException("Nombre vacío")
                
            except (TimeoutException, NoSuchElementException):
                # Si no se encuentra el nombre, buscar mensajes de error
                try:
                    # Buscar posibles mensajes de error en la página
                    error_selectors = [
                        "//div[contains(@class, 'alert')]",
                        "//div[contains(@class, 'error')]",
                        "//span[contains(@class, 'error')]",
                        "//div[contains(text(), 'No se encontr')]",
                        "//span[contains(text(), 'No se encontr')]"
                    ]
                    
                    error_message = "No se encontró información para los datos proporcionados"
                    
                    for selector in error_selectors:
                        try:
                            error_element = self.driver.find_element(By.XPATH, selector)
                            if error_element.text.strip():
                                error_message = error_element.text.strip()
                                break
                        except:
                            continue
                            
                except:
                    error_message = "No se encontró información para los datos proporcionados"
                
                execution_time = time.time() - start_time
                
                result = {
                    "status": "not_found",
                    "message": error_message,
                    "nuip": nuip,
                    "fecha_expedicion": fecha_expedicion,
                    "name": None,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "execution_time_seconds": round(execution_time, 2)
                }
                
                print(f"⚠️ No se encontró información para NUIP: {nuip}")
                return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            result = {
                "status": "error",
                "message": f"Error durante la consulta: {str(e)}",
                "nuip": nuip,
                "fecha_expedicion": fecha_expedicion,
                "name": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_time_seconds": round(execution_time, 2)
            }
            
            print(f"❌ Error al consultar NUIP {nuip}: {e}")
            return result
    
    def scrape_multiple_names(self, queries, delay=5):
        """
        Consulta múltiples nombres
        
        Args:
            queries (list): Lista de diccionarios con 'nuip' y 'fecha_expedicion'
            delay (int): Delay en segundos entre consultas
        
        Returns:
            list: Lista de resultados
        """
        results = []
        total = len(queries)
        
        print(f"🚀 Iniciando consulta de {total} nombres...")
        
        for i, query in enumerate(queries):
            print(f"📋 Procesando {i+1}/{total}: NUIP {query['nuip']}")
            
            result = self.scrape_name_by_nuip(query['nuip'], query['fecha_expedicion'])
            results.append(result)
            
            # Delay entre consultas si no es la última
            if i < total - 1:
                print(f"⏳ Esperando {delay} segundos...")
                time.sleep(delay)
        
        print(f"✅ Consulta completada. {len(results)} resultados obtenidos")
        return results
    
    def close(self):
        """Cierra el driver del navegador"""
        if self.driver:
            self.driver.quit()
            print("🔒 Driver cerrado correctamente")


def save_police_results(result, filename=None):
    """
    Guarda los resultados de la consulta de policía en un archivo JSON
    
    Args:
        result (dict or list): Resultado(s) de la consulta
        filename (str): Nombre del archivo (opcional)
    """
    try:
        # Crear directorio de resultados si no existe
        results_dir = "police_results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Generar nombre de archivo si no se proporciona
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"police_query_{timestamp}.json"
        
        filepath = os.path.join(results_dir, filename)
        
        # Guardar resultados
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados guardados en: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error al guardar resultados: {e}")
        return None


def load_queries_from_file(filepath):
    """
    Carga consultas desde un archivo JSON
    
    Args:
        filepath (str): Ruta del archivo JSON
    
    Returns:
        list: Lista de consultas
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            queries = json.load(f)
        
        print(f"📂 Cargadas {len(queries)} consultas desde {filepath}")
        return queries
        
    except Exception as e:
        print(f"❌ Error al cargar consultas: {e}")
        return []


def create_sample_queries_file():
    """Crea un archivo de ejemplo con consultas"""
    sample_queries = [
        {
            "nuip": "1102877148",
            "fecha_expedicion": "15/03/1990"
        },
        {
            "nuip": "1234567890",
            "fecha_expedicion": "01/01/1985"
        }
    ]
    
    filename = "sample_queries.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sample_queries, f, indent=2, ensure_ascii=False)
        
        print(f"📝 Archivo de ejemplo creado: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error al crear archivo de ejemplo: {e}")
        return None


def generate_report(results):
    """
    Genera un reporte resumen de los resultados
    
    Args:
        results (list): Lista de resultados
    
    Returns:
        dict: Reporte resumen
    """
    if not results:
        return {"error": "No hay resultados para procesar"}
    
    total = len(results)
    successful = len([r for r in results if r.get("status") == "success"])
    not_found = len([r for r in results if r.get("status") == "not_found"])
    errors = len([r for r in results if r.get("status") == "error"])
    
    # Calcular tiempo promedio de ejecución
    execution_times = [r.get("execution_time_seconds", 0) for r in results]
    avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
    
    report = {
        "summary": {
            "total_queries": total,
            "successful": successful,
            "not_found": not_found,
            "errors": errors,
            "success_rate": round((successful / total) * 100, 2) if total > 0 else 0,
            "average_execution_time": round(avg_time, 2)
        },
        "successful_results": [r for r in results if r.get("status") == "success"],
        "failed_results": [r for r in results if r.get("status") != "success"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return report


def test_police_scraper():
    """Función de prueba para el scraper de policía"""
    scraper = PoliciaScraperAuto(headless=False)
    
    try:
        # Prueba con un NUIP de ejemplo
        result = scraper.scrape_name_by_nuip("1102877148", "15/03/1990")
        print("Resultado de la prueba:", json.dumps(result, indent=2, ensure_ascii=False))
        
        # Guardar resultado
        save_police_results(result)
        
    finally:
        scraper.close()


def main():
    """Función principal para ejecutar consultas masivas"""
    print("🚀 Scraper de Policía Nacional - Consulta de Nombres")
    print("=" * 50)
    
    # Crear archivo de ejemplo si no existe
    if not os.path.exists("sample_queries.json"):
        create_sample_queries_file()
    
    # Cargar consultas
    queries_file = input("Ingrese la ruta del archivo de consultas (Enter para usar sample_queries.json): ").strip()
    if not queries_file:
        queries_file = "sample_queries.json"
    
    queries = load_queries_from_file(queries_file)
    if not queries:
        print("❌ No se pudieron cargar las consultas")
        return
    
    # Configurar scraper
    headless = input("¿Ejecutar en modo headless? (y/n, default: y): ").strip().lower()
    headless = headless != 'n'
    
    delay = input("Delay entre consultas en segundos (default: 5): ").strip()
    try:
        delay = int(delay) if delay else 5
    except ValueError:
        delay = 5
    
    # Ejecutar scraping
    scraper = PoliciaScraperAuto(headless=headless)
    
    try:
        results = scraper.scrape_multiple_names(queries, delay=delay)
        
        # Guardar resultados
        save_police_results(results)
        
        # Generar y mostrar reporte
        report = generate_report(results)
        print("\n📊 REPORTE FINAL:")
        print("=" * 30)
        print(f"Total de consultas: {report['summary']['total_queries']}")
        print(f"Exitosas: {report['summary']['successful']}")
        print(f"No encontradas: {report['summary']['not_found']}")
        print(f"Errores: {report['summary']['errors']}")
        print(f"Tasa de éxito: {report['summary']['success_rate']}%")
        print(f"Tiempo promedio: {report['summary']['average_execution_time']}s")
        
        # Guardar reporte
        save_police_results(report, "police_report.json")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    # Descomenta la línea que quieras usar:
    test_police_scraper()  # Para prueba individual
    # main()  # Para consultas masivas