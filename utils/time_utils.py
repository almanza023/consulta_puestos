import time
from datetime import datetime

def format_execution_time(seconds: float) -> str:
    """Formatea el tiempo de ejecución en un formato legible"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.2f}s"

def calculate_response_time(start_time: float) -> tuple:
    """
    Calcula el tiempo de respuesta y lo formatea
    
    Returns:
        tuple: (response_time_seconds, formatted_time)
    """
    end_time = time.time()
    response_time = end_time - start_time
    return round(response_time, 4), format_execution_time(response_time)

def get_current_timestamp() -> str:
    """Obtiene el timestamp actual en formato ISO"""
    return datetime.now().isoformat()