from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
import sys
import time
from datetime import datetime
import uuid

# Importar tu clase existente
from config import settings
from main import RegistraduriaScraperAuto, save_results

# Modelos Pydantic para la API
class NuipRequest(BaseModel):
    nuip: str = Field(..., description="Número único de identificación personal")
    
class MultipleNuipRequest(BaseModel):
    nuips: List[str] = Field(..., description="Lista de NUIPs a consultar")
    delay: Optional[int] = Field(5, description="Delay en segundos entre consultas")

class ScrapingResponse(BaseModel):
    status: str
    message: Optional[str] = None
    nuip: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    total_records: Optional[int] = None
    timestamp: str

class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    created_at: str
    completed_at: Optional[str] = None

# Crear la aplicación FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# Almacenamiento en memoria para trabajos (en producción usar Redis o base de datos)
jobs_storage: Dict[str, JobStatus] = {}

# Configuración global
API_KEY = os.getenv('APIKEY_2CAPTCHA')
if not API_KEY:
    print("❌ Error: No se encontró la API key de 2captcha")
    sys.exit(1)

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    print("🚀 Iniciando Registraduría Scraper API...")
    print(f"🔑 API Key configurada: {API_KEY[:10]}...")

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "Registraduría Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "single_query": "/scrape/single",
            "multiple_query": "/scrape/multiple",
            "async_multiple": "/scrape/async-multiple",
            "job_status": "/jobs/{job_id}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Endpoint de salud de la API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY)
    }

@app.post("/scrape/single", response_model=ScrapingResponse)
async def scrape_single_nuip(request: NuipRequest):
    """
    Consulta un solo NUIP de forma síncrona
    """
    try:
        # Crear scraper
        scraper = RegistraduriaScraperAuto(API_KEY, headless=True)
        
        try:
            # Realizar consulta
            result = scraper.scrape_nuip(request.nuip)
            
            # Convertir a modelo de respuesta
            response = ScrapingResponse(
                status=result.get("status", "unknown"),
                message=result.get("message"),
                nuip=result.get("nuip"),
                data=result.get("data"),
                total_records=result.get("total_records"),
                timestamp=result.get("timestamp", datetime.now().isoformat())
            )
            
            return response
            
        finally:
            scraper.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la consulta: {str(e)}"
        )

@app.post("/scrape/multiple")
async def scrape_multiple_nuips(request: MultipleNuipRequest):
    """
    Consulta múltiples NUIPs de forma síncrona
    """
    try:
        if len(request.nuips) > 50:  # Límite de seguridad
            raise HTTPException(
                status_code=400,
                detail="Máximo 50 NUIPs por consulta. Use el endpoint async para consultas más grandes."
            )
        
        # Crear scraper
        scraper = RegistraduriaScraperAuto(API_KEY, headless=True)
        
        try:
            # Realizar consultas
            results = scraper.scrape_multiple_nuips(request.nuips, request.delay)
            
            # Guardar resultados
            filename = save_results(results)
            
            return {
                "status": "completed",
                "total_processed": len(results),
                "results": results,
                "file_saved": filename,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            scraper.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar las consultas: {str(e)}"
        )

@app.post("/scrape/async-multiple")
async def scrape_multiple_nuips_async(request: MultipleNuipRequest, background_tasks: BackgroundTasks):
    """
    Consulta múltiples NUIPs de forma asíncrona usando background tasks
    """
    # Generar ID único para el trabajo
    job_id = str(uuid.uuid4())
    
    # Crear registro del trabajo
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        progress={"total": len(request.nuips), "completed": 0},
        created_at=datetime.now().isoformat()
    )
    
    jobs_storage[job_id] = job_status
    
    # Agregar tarea en segundo plano
    background_tasks.add_task(
        process_multiple_nuips_background,
        job_id,
        request.nuips,
        request.delay
    )
    
    return {
        "job_id": job_id,
        "status": "accepted",
        "message": f"Procesando {len(request.nuips)} NUIPs en segundo plano",
        "check_status_url": f"/jobs/{job_id}"
    }

async def process_multiple_nuips_background(job_id: str, nuips: List[str], delay: int):
    """
    Función para procesar NUIPs en segundo plano
    """
    try:
        # Actualizar estado a "running"
        jobs_storage[job_id].status = "running"
        
        # Crear scraper
        scraper = RegistraduriaScraperAuto(API_KEY, headless=True)
        
        try:
            results = []
            total = len(nuips)
            
            for i, nuip in enumerate(nuips):
                # Procesar NUIP
                result = scraper.scrape_nuip(nuip)
                results.append(result)
                
                # Actualizar progreso
                jobs_storage[job_id].progress = {
                    "total": total,
                    "completed": i + 1,
                    "current_nuip": nuip
                }
                
                # Delay entre consultas (excepto en la última)
                if i < total - 1:
                    await asyncio.sleep(delay)
            
            # Guardar resultados
            filename = save_results(results, f"resultados/async_results_{job_id}.json")
            
            # Actualizar estado final
            jobs_storage[job_id].status = "completed"
            jobs_storage[job_id].result = {
                "total_processed": len(results),
                "results": results,
                "file_saved": filename
            }
            jobs_storage[job_id].completed_at = datetime.now().isoformat()
            
        finally:
            scraper.close()
            
    except Exception as e:
        # Actualizar estado de error
        jobs_storage[job_id].status = "failed"
        jobs_storage[job_id].result = {"error": str(e)}
        jobs_storage[job_id].completed_at = datetime.now().isoformat()

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Obtiene el estado de un trabajo asíncrono
    """
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    return jobs_storage[job_id]

@app.get("/jobs")
async def list_jobs():
    """
    Lista todos los trabajos
    """
    return {
        "total_jobs": len(jobs_storage),
        "jobs": list(jobs_storage.values())
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Elimina un trabajo del almacenamiento
    """
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    
    del jobs_storage[job_id]
    return {"message": "Trabajo eliminado exitosamente"}

@app.get("/balance")
async def get_2captcha_balance():
    """
    Obtiene el balance de la cuenta de 2captcha
    """
    try:
        from main import TwoCaptchaSolver
        solver = TwoCaptchaSolver(API_KEY)
        balance = solver.get_balance()
        return {"balance": balance}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener balance: {str(e)}"
        )

# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )