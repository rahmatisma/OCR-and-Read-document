from flask import Flask, request, jsonify
import tempfile
import uuid
import requests
import json
from main import pengecekan_file

app = Flask(__name__)

# ============================================
# KONFIGURASI
# ============================================
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "phi3:mini"  # atau "dolphin-llama3:8b" untuk production

# ============================================
# ENDPOINT EXISTING (PDF Processing)
# ============================================
@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    """Endpoint existing untuk process PDF"""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "File not provided"}), 400

    try:
        # simpan sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            pdf_path = tmp.name

        # jalankan pipeline (harus return dict!)
        result = pengecekan_file(pdf_path)

        if not isinstance(result, dict):
            return jsonify({"error": "pengecekan_file must return JSON(dict)"}), 500

        # generate nama output
        json_filename = f"{uuid.uuid4()}.json"

        return jsonify({
            "message": "processed ok",
            "filename": json_filename,
            "data": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================
# RAG ENDPOINTS (NEW)
# ============================================

@app.route('/generate-embedding', methods=['POST'])
def generate_embedding():
    """
    Generate embedding dari text menggunakan Ollama
    
    Request Body:
    {
        "text": "Text yang ingin di-embed",
        "model": "nomic-embed-text"  // optional
    }
    
    Response:
    {
        "embedding": [0.123, -0.456, ...],
        "model": "nomic-embed-text",
        "dimension": 384
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Text is required"}), 400
        
        text = data['text']
        model = data.get('model', EMBEDDING_MODEL)
        
        # Call Ollama API untuk generate embedding
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({
                "error": "Ollama API error",
                "details": response.text
            }), 500
        
        result = response.json()
        embedding = result.get('embedding', [])
        
        return jsonify({
            "embedding": embedding,
            "model": model,
            "dimension": len(embedding)
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Failed to connect to Ollama",
            "details": str(e)
        }), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """
    Chat dengan Ollama menggunakan context dari RAG
    
    Request Body:
    {
        "query": "Pertanyaan user",
        "context": "Context dari similarity search",
        "model": "phi3:mini"  // optional
    }
    
    Response:
    {
        "answer": "Jawaban dari chatbot",
        "model": "phi3:mini"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Query is required"}), 400
        
        query = data['query']
        context = data.get('context', '')
        model = data.get('model', CHAT_MODEL)
        
        # Build prompt dengan context
        prompt = build_rag_prompt(query, context)
        
        # Call Ollama API
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            },
            timeout=300
        )
        
        if response.status_code != 200:
            return jsonify({
                "error": "Ollama API error",
                "details": response.text
            }), 500
        
        result = response.json()
        answer = result.get('response', '')
        
        return jsonify({
            "answer": answer,
            "model": model
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Failed to connect to Ollama",
            "details": str(e)
        }), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    
    Response:
    {
        "status": "online",
        "ollama_status": "online",
        "available_models": ["phi3:mini", "nomic-embed-text"]
    }
    """
    try:
        # Check Ollama connection
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        
        if response.status_code == 200:
            models_data = response.json()
            available_models = [m['name'] for m in models_data.get('models', [])]
            ollama_status = "online"
        else:
            available_models = []
            ollama_status = "offline"
    
    except Exception as e:
        available_models = []
        ollama_status = "offline"
    
    return jsonify({
        "status": "online",
        "ollama_status": ollama_status,
        "ollama_url": OLLAMA_BASE_URL,
        "available_models": available_models,
        "embedding_model": EMBEDDING_MODEL,
        "chat_model": CHAT_MODEL
    })


# ============================================
# HELPER FUNCTIONS
# ============================================

def build_rag_prompt(query: str, context: str) -> str:
    """
    Build prompt untuk RAG chatbot
    """
    prompt = f"""Anda adalah asisten AI yang membantu menjawab pertanyaan tentang data SPK (Surat Perintah Kerja) dan jaringan.

INSTRUKSI:
1. Jawab pertanyaan HANYA berdasarkan CONTEXT yang diberikan
2. Jika informasi tidak ada di context, katakan "Informasi tidak tersedia dalam database"
3. Jawab dalam Bahasa Indonesia yang natural dan jelas
4. Jika ada nomor jaringan (nojar), nomor SPK, nama pelanggan, atau data teknis, sebutkan dengan jelas
5. Berikan jawaban yang spesifik dan to the point

CONTEXT:
{context}

PERTANYAAN USER:
{query}

JAWABAN:"""
    
    return prompt


# ============================================
# RUN APP
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Flask API Server Starting...")
    print("=" * 50)
    print(f"📍 Server URL: http://localhost:5000")
    print(f"🤖 Ollama URL: {OLLAMA_BASE_URL}")
    print(f"📊 Embedding Model: {EMBEDDING_MODEL}")
    print(f"💬 Chat Model: {CHAT_MODEL}")
    print("=" * 50)
    print("\nAvailable Endpoints:")
    print("  POST /process-pdf          - Process PDF document")
    print("  POST /generate-embedding   - Generate text embedding")
    print("  POST /chat                 - Chat with RAG context")
    print("  GET  /health              - Health check")
    print("=" * 50)
    
    app.run(port=5000, debug=True)