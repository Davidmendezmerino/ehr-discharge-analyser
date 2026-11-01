from fastapi import FastAPI, HTTPException, Query

from models.schemas import (
    ExtractRequest,
    ExtractResponse,
    InferRequest,
    InferResponse,
)
from services.infer_service import run_inference

app = FastAPI(title="EHR Demo API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/clip/extract", response_model=ExtractResponse)
def clip_extract(req: ExtractRequest):
    return ExtractResponse(spans=[])


@app.post("/clip/infer", response_model=InferResponse)
def clip_infer(req: InferRequest):
    if len(req.text) > 50_000:
        raise HTTPException(status_code=413, detail="Text exceeds 50,000 character limit")
    try:
        return run_inference(req.text)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/deid/redact")
def deid_redact(req: ExtractRequest):
    return {"redacted_text": req.text, "spans": []}