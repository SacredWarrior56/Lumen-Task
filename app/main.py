# main.py
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from app.logging_utils import get_logger
from app.selenium_service import get_chatgpt_answer
from fastapi.staticfiles import StaticFiles

API_KEY = "lumen"

app = FastAPI()


logger = get_logger(__name__)

class PromptRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return {"status": "ok",
            "message": "Welcome to the ChatGPT API Service",
            "instruction": "/docs for API swagger UI",
           }

@app.get("/health")
def health_check():
    logger.info("Health check called")
    return {"status": "ok"}

@app.post("/generate")
def generate(req: PromptRequest, x_api_key: str = Header(...)):
    check_api_key(x_api_key)

    if not req.prompt:
        raise HTTPException(400, "Prompt is required")
    try:
        answer = get_chatgpt_answer(req.prompt)
        return {"status": "ok", "answer": answer}
    except Exception as e:
        logger.exception("Error generating response")
        return {"status": "error", "message": str(e)}
    
def check_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")