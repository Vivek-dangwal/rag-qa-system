import uvicorn
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field
import requests
from pypdf import PdfReader
import io
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import time

app = FastAPI(title="RAG-Based Question Answering System")

# --- 1. CONFIG & MODELS ---
GOOGLE_API_KEY = "AIzaSyAD9xTeq74PbujqoXSMfOlqT0TSwXH-qzA"
embed_model = SentenceTransformer('all-MiniLM-L6-v2') 
index = faiss.IndexFlatL2(384) 
doc_chunks = [] 

# Rate Limiting Storage
last_request_time = {}

# --- 2. REQUEST VALIDATION (Requirement: Pydantic) ---
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=500, description="The question to ask the document")

# --- 3. DYNAMIC MODEL DISCOVERY ---
def get_working_url():
    base = "https://generativelanguage.googleapis.com/v1beta"
    try:
        r = requests.get(f"{base}/models?key={GOOGLE_API_KEY}").json()
        for m in r.get('models', []):
            if 'flash' in m['name'].lower(): 
                return f"{base}/{m['name']}:generateContent?key={GOOGLE_API_KEY}"
    except: pass
    return f"{base}/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"

# --- 4. BACKGROUND JOB: CHUNKING & EMBEDDING (Requirement: Background Jobs) ---
def ingest_text(text: str):
    global doc_chunks
    # Requirement: Chunking Strategy (500 chars, 50 overlap)
    chunk_size = 500
    overlap = 50
    new_chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]
    
    if new_chunks:
        embeddings = embed_model.encode(new_chunks)
        index.add(np.array(embeddings).astype('float32'))
        doc_chunks.extend(new_chunks)

@app.get("/")
def home():
    return {"status": "Online", "requirement_check": "Pydantic, Rate-Limiting, FAISS, and Background Jobs active."}

@app.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    content = await file.read()
    # Requirement: Accept PDF and TXT
    if file.filename.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        text = "".join([p.extract_text() or "" for p in reader.pages])
    elif file.filename.endswith(".txt"):
        text = content.decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or TXT.")
    
    background_tasks.add_task(ingest_text, text)
    return {"message": f"Ingesting {file.filename} in background..."}

@app.post("/ask") # Using POST for Pydantic validation body
async def ask_question(request: QuestionRequest, req_details: Request):
    # Requirement: Basic Rate Limiting
    client_ip = req_details.client.host
    current_time = time.time()
    if client_ip in last_request_time and (current_time - last_request_time[client_ip]) < 2:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Wait 2 seconds.")
    last_request_time[client_ip] = current_time

    if not doc_chunks:
        raise HTTPException(status_code=404, detail="No documents indexed. Upload a file first.")
    
    # Requirement: Similarity Search
    q_emb = embed_model.encode([request.question])
    distances, indices = index.search(np.array(q_emb).astype('float32'), k=3)
    
    context = "\n".join([doc_chunks[i] for i in indices[0] if i != -1])
    
    # Requirement: Generate using LLM
    payload = {
        "contents": [{"parts": [{"text": f"Context: {context}\n\nQuestion: {request.question}"}]}]
    }
    
    try:
        response = requests.post(get_working_url(), json=payload)
        result = response.json()
        answer = result['candidates'][0]['content']['parts'][0]['text']
        return {"answer": answer, "sources_retrieved": len(indices[0])}
    except Exception as e:
        return {"error": "LLM Failure", "debug": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)