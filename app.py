# app.py
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import subprocess
import uuid
import os
import sys
import shutil

app = FastAPI()

# Carpeta global para outputs
os.makedirs("outputs", exist_ok=True)
app.mount("/static", StaticFiles(directory="outputs", html=True), name="static")

# Carpeta fija para el "último" modelo generado
FIXED_OUTPUT_DIR = os.path.join("outputs", "current")
os.makedirs(FIXED_OUTPUT_DIR, exist_ok=True)

# Leer token de Hugging Face desde variable de entorno
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("⚠️ Advertencia: no se ha definido HF_TOKEN en las variables de entorno.")

@app.get("/favicon.ico")
async def favicon():
    return PlainTextResponse("", status_code=204)

@app.get("/static/{path:path}")
async def static_no_cache(path: str):
    full_path = os.path.join("outputs", path)
    return FileResponse(
        full_path,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.post("/reconstruct")
async def reconstruct(
    request: Request,
    file: UploadFile = File(...)
):
    try:
        # Guardar imagen temporal
        temp_filename = f"temp_{uuid.uuid4()}.png"
        with open(temp_filename, "wb") as f:
            f.write(await file.read())

        # Limpiar carpeta de salida antes de generar el nuevo modelo
        if os.path.exists(FIXED_OUTPUT_DIR):
            shutil.rmtree(FIXED_OUTPUT_DIR)
        os.makedirs(FIXED_OUTPUT_DIR, exist_ok=True)

        # Construir comando para run.py
        cmd = [
            sys.executable, "run.py", temp_filename,
            "--output-dir", FIXED_OUTPUT_DIR
        ]

        # Pasar token Hugging Face como variable de entorno
        env = os.environ.copy()
        if HF_TOKEN:
            env["HF_TOKEN"] = HF_TOKEN

        # Ejecutar run.py
        subprocess.run(cmd, check=True, env=env)

        # Buscar modelo 3D (.glb)
        model_path = None
        for root, _, files in os.walk(FIXED_OUTPUT_DIR):
            for f in files:
                if f.endswith(".glb"):
                    model_path = os.path.join(root, f)
                    break

        if not model_path:
            return JSONResponse({"error": "No se generó ningún modelo"}, status_code=500)

        # Construir URL accesible
        base_url = str(request.base_url)
        model_rel_path = os.path.relpath(model_path, "outputs")
        model_url = f"{base_url}static/{model_rel_path.replace(os.sep, '/')}"

        # Borrar imagen temporal
        os.remove(temp_filename)

        return JSONResponse({
            "model_url": model_url
        })

    except subprocess.CalledProcessError as e:
        return JSONResponse({"error": f"Fallo en run.py: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080)
