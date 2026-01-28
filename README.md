# RAG-Based Question Answering System

A high-performance Retrieval-Augmented Generation (RAG) API built with FastAPI. This system allows users to upload documents (PDF/TXT) and ask questions based strictly on the provided content.

## 🚀 Features
- **Asynchronous Ingestion**: Uses FastAPI BackgroundTasks for non-blocking document processing.
- **Vector Storage**: Utilizes FAISS for efficient similarity search.
- **Dynamic Model Discovery**: Automatically detects and uses the best available Gemini model.
- **Semantic Chunking**: Implements a 500-character chunking strategy with overlap for context retention.

## 🏗️ Architecture
The system follows a standard RAG pipeline:
1. **Document Loading**: Extracts text from PDF or TXT.
2. **Chunking**: Splits text into 500-character segments.
3. **Embedding**: Generates vectors using `all-MiniLM-L6-v2`.
4. **Vector Store**: Stores embeddings in a FAISS index.
5. **Retrieval**: Finds the Top-K (3) relevant chunks via similarity search.
6. **Generation**: Sends context + query to Gemini 2.5 Flash for the final answer.

## 🛠️ Setup Instructions
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the server: `python main.py`
4. Access the API documentation at `http://127.0.0.1:8000/docs`

## 📊 Evaluation Metrics
- **Latency**: Retrieval typically completes in under 50ms.
- **Accuracy**: Answers are grounded in retrieved chunks to prevent hallucinations.