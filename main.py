import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar las clases desde el archivo separado
from registraduria_scraper import RegistraduriaScraperAuto, TwoCaptchaSolver, save_registraduria_results

# Re-exportar para mantener compatibilidad con imports existentes
__all__ = ['RegistraduriaScraperAuto', 'TwoCaptchaSolver', 'save_registraduria_results']

# Función de compatibilidad para save_results (mantener el nombre original)
def save_results(data, filename=None):
    """Función de compatibilidad para mantener el nombre original"""
    return save_registraduria_results(data, filename)

# Ejemplo de uso directo
if __name__ == "__main__":
    # Cargar API key desde variables de entorno
    API_KEY = os.getenv('APIKEY_2CAPTCHA')
    
    # Verificar que la API key esté disponible
    if not API_KEY:
        print("❌ Error: No se encontró la API key de 2captcha")
        print("Asegúrate de que el archivo .env contenga: APIKEY_2CAPTCHA=tu_api_key")
        sys.exit(1)
    
    print(f"🔑 API Key cargada: {API_KEY[:10]}...")
    
    # Crear scraper
    scraper = RegistraduriaScraperAuto(API_KEY, headless=False)
    
    try:
        # Ejemplo de consulta
        nuip_ejemplo = "1102877148"
        resultado = scraper.scrape_nuip(nuip_ejemplo)
        
        print(f"\n📊 RESULTADO FINAL:")
        import json
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