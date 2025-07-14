from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import re
from datetime import datetime

class NuipRequest(BaseModel):
    nuip: str = Field(..., description="Número único de identificación personal")
    
class MultipleNuipRequest(BaseModel):
    nuips: List[str] = Field(..., description="Lista de NUIPs a consultar")
    delay: Optional[int] = Field(5, description="Delay en segundos entre consultas")

class PoliceNameRequest(BaseModel):
    nuip: str = Field(..., description="Número único de identificación personal")
    fecha_expedicion: str = Field(..., description="Fecha de expedición en formato dd/mm/yyyy")
    
    @validator('fecha_expedicion')
    def validate_fecha_format(cls, v):
        # Validar formato dd/mm/yyyy
        pattern = r'^(\d{2})/(\d{2})/(\d{4})$'
        if not re.match(pattern, v):
            raise ValueError('La fecha debe estar en formato dd/mm/yyyy')
        
        # Validar que sea una fecha válida
        try:
            day, month, year = map(int, v.split('/'))
            datetime(year, month, day)
        except ValueError:
            raise ValueError('Fecha inválida')
        
        return v

class PoliceQuery(BaseModel):
    nuip: str = Field(..., description="Número único de identificación personal")
    fecha_expedicion: str = Field(..., description="Fecha de expedición en formato dd/mm/yyyy")
    
    @validator('fecha_expedicion')
    def validate_fecha_format(cls, v):
        # Validar formato dd/mm/yyyy
        pattern = r'^(\d{2})/(\d{2})/(\d{4})$'
        if not re.match(pattern, v):
            raise ValueError('La fecha debe estar en formato dd/mm/yyyy')
        
        # Validar que sea una fecha válida
        try:
            day, month, year = map(int, v.split('/'))
            datetime(year, month, day)
        except ValueError:
            raise ValueError('Fecha inválida')
        
        return v

class MultiplePoliceNameRequest(BaseModel):
    queries: List[PoliceQuery] = Field(..., description="Lista de consultas de policía")
    delay: Optional[int] = Field(3, description="Delay en segundos entre consultas")
    
    @validator('queries')
    def validate_queries_length(cls, v):
        if len(v) == 0:
            raise ValueError('Debe proporcionar al menos una consulta')
        if len(v) > 100:
            raise ValueError('Máximo 100 consultas por request')
        return v