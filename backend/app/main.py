import logging
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import ollama
import json

# ==== Logging config ====
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s [%(name)s] %(message)s"
)
logger = logging.getLogger("codemaster-ai")

# ==== Ollama client config ====
OLLAMA_HOST = "http://ollama:11434"
try:
    client = ollama.Client(host=OLLAMA_HOST)
except Exception as e:
    logger.error(f"❌ Ollama client init failed: {e}")
    client = None

# ==== FastAPI app ====
app = FastAPI(
    title="Codemaster-AI Ultra Boss",
    description="Brutal AI code agent with full safety & zero crash tolerance",
    version="9.9.9"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

# === AI activation flag ===
activated = False

# ==== Models ====
class CodeRequest(BaseModel):
    prompt: str
    language: Optional[str] = None
    model: Optional[str] = None

class CodeResponse(BaseModel):
    code: str
    explanation: str
    confidence: float
    model_used: str
    elapsed_ms: int

# ==== Brutal model selector ====
def select_best_model(prompt: str, language: Optional[str]) -> Dict[str, str]:
    p = (prompt or "").lower()
    l = (language or "").lower()
    mapping = [
        ("mistral:7b-instruct", "Data Science/ML detected", lambda: any(x in p for x in [
            "machine learning","ml","pandas","numpy","dataframe","scikit","keras",
            "data science","deep learning","regression","classification","training","inference","stats"
        ])),
        ("codellama:7b-instruct", "Python detected", lambda: "python" in l or "python" in p),
        ("qwen2.5-coder:7b", "JavaScript/Web detected", lambda: "javascript" in l or "js" in l or any(x in p for x in [
            "javascript","js","web","html","css","browser","frontend","react","vue"
        ])),
        ("mistral:7b-instruct", "Java detected", lambda: "java" in l or "java" in p),
        ("mistral:7b-instruct", "C/C++ detected", lambda: any(x in l for x in ["c++","cpp","c language"]) or any(x in p for x in ["c++","cpp"])),
        ("mistral:7b-instruct", "C# detected", lambda: "c#" in l or "c#" in p),
        ("mistral:7b-instruct", "Go detected", lambda: "go" in l or "golang" in l or "go lang" in p),
        ("mistral:7b-instruct", "Rust detected", lambda: "rust" in l or "rust" in p),
        ("mistral:7b-instruct", "Ruby detected", lambda: "ruby" in l or "ruby" in p),
        ("mistral:7b-instruct", "TypeScript detected", lambda: "typescript" in l or "typescript" in p),
        ("mistral:7b-instruct", "Swift/Kotlin detected", lambda: any(x in l for x in ["swift","kotlin"]) or any(x in p for x in ["swift","kotlin","android","ios"])),
        ("qwen2.5-coder:7b", "SQL/Database detected", lambda: "sql" in l or "sql" in p or any(x in p for x in [
            "query","database","mysql","postgres","sqlite","mongodb","oracle","db","table","column"
        ])),
        ("qwen2.5-coder:7b", "Shell/Bash detected", lambda: any(x in l for x in ["bash","shell","sh"]) or any(x in p for x in [
            "shell script","bash script","automation","cli","powershell"
        ])),
        ("qwen2.5-coder:7b", "PHP detected", lambda: "php" in l or "php" in p),
        ("qwen2.5-coder:7b", "DevOps detected", lambda: any(x in l for x in ["yaml","docker","compose"]) or any(x in p for x in [
            "yaml","docker","docker-compose","kubernetes"
        ])),
        ("qwen2.5-coder:7b", "Frontend/UI/UX detected", lambda: any(x in l for x in ["html","css"]) or any(x in p for x in [
            "html","css","ui","ux","responsive","design"
        ])),
        ("mistral:7b-instruct", "Statistical/Matlab/R/SAS detected", lambda: any(x in l for x in ["matlab","r","sas"]) or any(x in p for x in [
            "matlab","r language","sas","regression analysis","statistical"
        ])),
    ]
    for model, reason, cond in mapping:
        try:
            if cond():
                logger.info(f"Model selected: {model} | Reason: {reason}")
                return {"model": model, "reason": reason}
        except Exception:
            continue
    logger.info("Model selected: qwen2.5-coder:7b | Reason: Default fallback")
    return {"model": "qwen2.5-coder:7b", "reason": "Default fallback"}

# ==== Middleware ====
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"{request.method} {request.url}")
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception("🔥 Unhandled error in request")
        raise
    finally:
        duration = (time.time() - start_time) * 1000
        logger.info(f"→ {request.method} {request.url} finished in {duration:.2f}ms")
    return response

# ==== Activate & Deactivate ====
@app.post("/activate")
async def activate_ai():
    global activated
    activated = True
    logger.info("✅ AI agent ACTIVATED.")
    return {"status": "activated", "message": "AI agent is active."}

@app.post("/deactivate")
async def deactivate_ai():
    global activated
    activated = False
    logger.info("🛑 AI agent DEACTIVATED.")
    return {"status": "deactivated", "message": "AI agent is inactive."}

# ==== Health ====
@app.get("/health")
async def health():
    if not client:
        return {"status": "unhealthy", "error": "Ollama client not initialized"}
    try:
        models = client.list()
        return {"status": "healthy", "models": [m["name"] for m in models.get("models", [])]}
    except Exception as e:
        logger.error(f"⚠️ Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

# ==== Models list ====
@app.get("/models")
async def models():
    if not client:
        raise HTTPException(status_code=500, detail="Ollama client not initialized")
    try:
        mlist = client.list()
        return {"models": [m["name"] for m in mlist.get("models", [])]}
    except Exception as e:
        logger.error(f"❌ Model list retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==== Generate code ====
@app.post("/generate-code", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    if not activated:
        raise HTTPException(status_code=403, detail="AI Agent inactive. Use /activate.")
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    if not client:
        raise HTTPException(status_code=500, detail="Ollama client not initialized")

    selection = select_best_model(request.prompt, request.language)
    chosen_model = request.model or selection["model"]
    task_prompt = (
        f"You are a brutal, expert-level AI programmer.\n"
        f"Generate clean, optimized {request.language or '[AUTO DETECTED]'} code for:\n{request.prompt}\n"
    )
    start = time.time()
    try:
        response = client.generate(model=chosen_model, prompt=task_prompt,
            options={"temperature":0.1,"top_p":0.9,"top_k":40})
    except Exception as ex:
        logger.exception("💥 Code generation failed")
        raise HTTPException(status_code=500, detail=f"Code generation failed: {ex}")
    elapsed = int((time.time()-start)*1000)
    code = getattr(response,"response",None) or (response.get("response") if isinstance(response,dict) else "")
    code = code.strip() if code else "// No code generated."
    logger.info(f"✅ Generated {len(code)} chars in {elapsed}ms with {chosen_model}")
    return CodeResponse(
        code=code,
        explanation=f"Generated by {chosen_model} ({selection['reason']}).",
        confidence=0.95,
        model_used=chosen_model,
        elapsed_ms=elapsed
    )

# ==== Fix code ====
class FixRequest(BaseModel):
    file_code: str
    instructions: Optional[str] = None

@app.post("/fix-code", response_model=CodeResponse)
async def fix_code(req: FixRequest):
    file_code = req.file_code
    instructions = req.instructions

    if not activated:
        raise HTTPException(status_code=403, detail="AI Agent inactive. Use /activate.")
    if not file_code or not file_code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")
    if not client:
        raise HTTPException(status_code=500, detail="Ollama client not initialized")

    prompt = (
        f"You are an expert senior developer.\nGiven this code:\n{file_code}\n\n"
        f"Instructions: {instructions or 'Fix all bugs and optimize for best practices.'}"
    )
    selection = select_best_model(file_code, None)
    chosen_model = selection["model"]
    start = time.time()
    try:
        response = client.generate(
            model=chosen_model,
            prompt=prompt,
            options={"temperature":0.1,"top_p":0.9,"top_k":40}
        )
    except Exception as e:
        logger.exception("💥 Code fix failed")
        raise HTTPException(status_code=500, detail=f"Code fixing failed: {str(e)}")
    elapsed = int((time.time()-start)*1000)
    code = getattr(response,"response",None) or (response.get("response") if isinstance(response,dict) else "")
    code = code.strip() if code else "// No fixes generated."
    logger.info(f"✅ Fixed code with {chosen_model} in {elapsed}ms")
    return CodeResponse(
        code=code,
        explanation=f"Fixed by {chosen_model} ({selection['reason']}).",
        confidence=0.95,
        model_used=chosen_model,
        elapsed_ms=elapsed
    )

# ==== Run server ====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
