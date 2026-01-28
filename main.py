import uvicorn
from fastapi import FastAPI, UploadFile, File
import requests
from pypdf import PdfReader
import io

app = FastAPI()

# --- CONFIGURATION ---
GOOGLE_API_KEY = "AIzaSyAD9xTeq74PbujqoXSMfOlqT0TSwXH-qzA"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

pdf_text_content = ""

def get_best_model():
    """Dynamically finds a working Flash model from your API list."""
    try:
        url = f"{BASE_URL}/models?key={GOOGLE_API_KEY}"
        response = requests.get(url).json()
        # Look for any 'flash' model that supports generating content
        for m in response.get('models', []):
            name = m['name']
            if 'flash' in name.lower() and 'generateContent' in m['supportedGenerationMethods']:
                return name # This will be something like 'models/gemini-1.5-flash-001'
        return "models/gemini-1.5-flash" # Fallback
    except:
        return "models/gemini-1.5-flash"

@app.get("/")
def home():
    working_model = get_best_model()
    return {"message": "Discovery System Active", "using_model": working_model}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    global pdf_text_content
    content = await file.read()
    pdf_reader = PdfReader(io.BytesIO(content))
    text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    pdf_text_content = text
    return {"message": "Document Received"}

@app.get("/ask")
async def ask_question(question: str):
    if not pdf_text_content:
        return {"error": "Upload PDF first"}
    
    # Get the model name that actually exists for your account
    model_name = get_best_model()
    ask_url = f"{BASE_URL}/{model_name}:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": f"Context: {pdf_text_content[:15000]}\n\nQuestion: {question}"}]}]
    }
    
    try:
        response = requests.post(ask_url, json=payload)
        result = response.json()
        answer = result['candidates'][0]['content']['parts'][0]['text']
        return {"question": question, "answer": answer, "model_used": model_name}
    except Exception as e:
        return {"error": "Processing failed", "debug": str(result) if 'result' in locals() else str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)