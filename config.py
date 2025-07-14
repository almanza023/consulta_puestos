import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_KEY_2CAPTCHA = os.getenv('APIKEY_2CAPTCHA')
    MAX_NUIPS_SYNC = 50
    DEFAULT_DELAY = 5
    HEADLESS_MODE = True
    
    # Configuración de la API
    API_TITLE = "API Consulta Puesto de Votación"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "API para consultar información de puestos de Votación Funete de datos Registraduría Nacional del Estado Civil"

settings = Settings()