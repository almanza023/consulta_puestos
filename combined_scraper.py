
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from registraduria_scraper import RegistraduriaScraperAuto, save_registraduria_results
from police_scraper import PoliciaScraperAuto, save_police_results

class CombinedScraper:
    """Scraper combinado para Registraduría y Policía Nacional"""
    
    def __init__(self, captcha_api_key: str, headless: bool = True):
        """
        Inicializa el scraper combinado
        
        Args:
            captcha_api_key (str): API key para 2captcha
            headless (bool): Si ejecutar en modo headless
        """
        self.captcha_api_key = captcha_api_key
        self.headless = headless
        self.registraduria_scraper = None
        self.police_scraper = None
    
    def setup_scrapers(self):
        """Inicializa ambos scrapers"""
        try:
            print("🔧 Configurando scrapers...")
            self.registraduria_scraper = RegistraduriaScraperAuto(
                self.captcha_api_key, 
                headless=self.headless
            )
            self.police_scraper = PoliciaScraperAuto(headless=self.headless)
            print("✅ Scrapers configurados correctamente")
        except Exception as e:
            print(f"❌ Error al configurar scrapers: {e}")
            raise
    
    def scrape_combined_data(self, nuip: str, fecha_expedicion: str) -> Dict[str, Any]:
        """
        Realiza consulta combinada en ambos sistemas
        
        Args:
            nuip (str): Número único de identificación personal
            fecha_expedicion (str): Fecha de expedición en formato dd/mm/yyyy
            
        Returns:
            Dict[str, Any]: Resultado combinado de ambas consultas
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"CONSULTA COMBINADA - NUIP: {nuip}")
        print(f"{'='*60}")
        
        result = {
            "status": "processing",
            "nuip": nuip,
            "fecha_expedicion": fecha_expedicion,
            "registraduria_result": None,
            "police_result": None,
            "timestamp": datetime.now().isoformat(),
            "response_time_seconds": 0.0,
            "execution_time": "0ms"
        }
        
        try:
            # Asegurar que los scrapers estén configurados
            if not self.registraduria_scraper or not self.police_scraper:
                self.setup_scrapers()
            
            # 1. Consulta en Registraduría
            print("\n🏛️ INICIANDO CONSULTA EN REGISTRADURÍA...")
            try:
                registraduria_result = self.registraduria_scraper.scrape_nuip(nuip)
                result["registraduria_result"] = registraduria_result
                print(f"✅ Consulta Registraduría completada: {registraduria_result.get('status', 'unknown')}")
            except Exception as e:
                print(f"❌ Error en consulta Registraduría: {e}")
                result["registraduria_result"] = {
                    "status": "error",
                    "message": f"Error en Registraduría: {str(e)}",
                    "nuip": nuip,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Pequeña pausa entre consultas
            time.sleep(2)
            
            # 2. Consulta en Policía Nacional
            print("\n👮 INICIANDO CONSULTA EN POLICÍA NACIONAL...")
            try:
                police_result = self.police_scraper.scrape_name_by_nuip(nuip, fecha_expedicion)
                result["police_result"] = police_result
                print(f"✅ Consulta Policía completada: {police_result.get('status', 'unknown')}")
            except Exception as e:
                print(f"❌ Error en consulta Policía: {e}")
                result["police_result"] = {
                    "status": "error",
                    "message": f"Error en Policía: {str(e)}",
                    "nuip": nuip,
                    "fecha_expedicion": fecha_expedicion,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Determinar estado general
            registraduria_success = result["registraduria_result"].get("status") == "success"
            police_success = result["police_result"].get("status") == "success"
            
            if registraduria_success and police_success:
                result["status"] = "success"
            elif registraduria_success or police_success:
                result["status"] = "partial_success"
            else:
                result["status"] = "failed"
            
            # Calcular tiempo de respuesta
            execution_time = time.time() - start_time
            result["response_time_seconds"] = round(execution_time, 2)
            result["execution_time"] = f"{round(execution_time * 1000)}ms"
            
            print(f"\n🎉 CONSULTA COMBINADA COMPLETADA")
            print(f"Estado final: {result['status']}")
            print(f"Tiempo total: {result['execution_time']}")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result.update({
                "status": "error",
                "message": f"Error general en consulta combinada: {str(e)}",
                "response_time_seconds": round(execution_time, 2),
                "execution_time": f"{round(execution_time * 1000)}ms"
            })
            print(f"❌ Error crítico en consulta combinada: {e}")
            return result
    
    def scrape_multiple_combined(self, queries: List[Dict[str, str]], delay: int = 5) -> List[Dict[str, Any]]:
        """
        Realiza múltiples consultas combinadas
        
        Args:
            queries (List[Dict]): Lista de consultas con 'nuip' y 'fecha_expedicion'
            delay (int): Delay entre consultas en segundos
            
        Returns:
            List[Dict[str, Any]]: Lista de resultados combinados
        """
        results = []
        total = len(queries)
        
        print(f"\n🚀 INICIANDO CONSULTA MASIVA COMBINADA")
        print(f"Total de consultas: {total}")
        print(f"Delay entre consultas: {delay} segundos")
        
        try:
            # Configurar scrapers una sola vez
            self.setup_scrapers()
            
            for i, query in enumerate(queries, 1):
                print(f"\n📋 Procesando consulta {i}/{total}")
                
                result = self.scrape_combined_data(
                    query["nuip"], 
                    query["fecha_expedicion"]
                )
                results.append(result)
                
                # Delay entre consultas (excepto en la última)
                if i < total:
                    print(f"⏳ Esperando {delay} segundos...")
                    time.sleep(delay)
            
            print(f"\n🎉 CONSULTA MASIVA COMBINADA COMPLETADA")
            print(f"Total procesado: {len(results)} consultas")
            
            return results
            
        except Exception as e:
            print(f"❌ Error en consulta masiva combinada: {e}")
            raise
    
    def close(self):
        """Cierra ambos scrapers"""
        try:
            if self.registraduria_scraper:
                self.registraduria_scraper.close()
                print("🔒 Scraper Registraduría cerrado")
            
            if self.police_scraper:
                self.police_scraper.close()
                print("🔒 Scraper Policía cerrado")
                
        except Exception as e:
            print(f"⚠️ Error al cerrar scrapers: {e}")

def save_combined_results(results, filename=None):
    """
    Guarda los resultados combinados en un archivo JSON
    
    Args:
        results: Resultado(s) de la consulta combinada
        filename (str): Nombre del archivo (opcional)
    """
    try:
        # Crear directorio de resultados si no existe
        results_dir = "combined_results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Generar nombre de archivo si no se proporciona
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"combined_query_{timestamp}.json"
        
        filepath = os.path.join(results_dir, filename)
        
        # Guardar resultados
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados combinados guardados en: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error al guardar resultados combinados: {e}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    import os
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    API_KEY = os.getenv('APIKEY_2CAPTCHA')
    if not API_KEY:
        print("❌ Error: No se encontró la API key de 2captcha")
        sys.exit(1)
    
    # Crear scraper combinado
    combined_scraper = CombinedScraper(API_KEY, headless=False)
    
    try:
        # Ejemplo de consulta individual
        resultado = combined_scraper.scrape_combined_data(
            nuip="1102877148",
            fecha_expedicion="15/03/1990"
        )
        
        print(f"\n📊 RESULTADO FINAL:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        # Guardar resultado
        save_combined_results(resultado)
        
    except KeyboardInterrupt:
        print("\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
    finally:
        combined_scraper.close()