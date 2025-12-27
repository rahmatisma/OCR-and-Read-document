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
CHAT_MODEL = "llama3.2:3b"  # atau "dolphin-llama3:8b" untuk production

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
# RAG ENDPOINTS
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
    Chat dengan Ollama menggunakan context dari RAG + Conversation History
    
    Request Body:
    {
        "query": "Pertanyaan user",
        "context": "Context dari similarity search",
        "conversation_history": [  // ✅ NEW
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "model": "llama3.2:3b"  // optional
    }
    
    Response:
    {
        "answer": "Jawaban dari chatbot",
        "model": "llama3.2:3b"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Query is required"}), 400
        
        query = data['query']
        context = data.get('context', '')
        conversation_history = data.get('conversation_history', [])  # ✅ NEW
        model = data.get('model', CHAT_MODEL)
        
        # ✅ Build prompt dengan context + conversation history
        prompt = build_rag_prompt(query, context, conversation_history)
        
        # ✅ Log request info
        print("=" * 60)
        print("📨 CHAT REQUEST")
        print("=" * 60)
        print(f"Query: {query}")
        print(f"Has Context: {len(context) > 0}")
        print(f"Context Length: {len(context)} chars")
        print(f"Has History: {len(conversation_history) > 0}")
        print(f"History Length: {len(conversation_history)} messages")
        if conversation_history:
            print("\n📜 Recent History:")
            for i, msg in enumerate(conversation_history[-3:]):  # Show last 3
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:50]  # First 50 chars
                print(f"  [{i+1}] {role.upper()}: {content}...")
        print("=" * 60)
        
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
                    "num_predict": 512,  # Max tokens untuk response
                }
            },
            timeout=300
        )
        
        if response.status_code != 200:
            print(f"❌ Ollama API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return jsonify({
                "error": "Ollama API error",
                "details": response.text
            }), 500
        
        result = response.json()
        answer = result.get('response', '').strip()
        
        # ✅ Log response info
        print("✅ CHAT RESPONSE GENERATED")
        print(f"Answer Length: {len(answer)} chars")
        print(f"Model Used: {model}")
        print("=" * 60)
        print()
        
        return jsonify({
            "answer": answer,
            "model": model
        })
    
    except requests.exceptions.Timeout:
        print("❌ Ollama request timeout")
        return jsonify({
            "error": "Request timeout",
            "details": "Ollama took too long to respond"
        }), 504
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama connection error: {str(e)}")
        return jsonify({
            "error": "Failed to connect to Ollama",
            "details": str(e)
        }), 500
    
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    
    Response:
    {
        "status": "online",
        "ollama_status": "online",
        "available_models": ["llama3.2:3b", "nomic-embed-text"]
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

def build_rag_prompt(query: str, context: str, conversation_history: list = None) -> str:
    """
    Build prompt untuk RAG chatbot dengan conversation history
    
    Args:
        query: Pertanyaan user saat ini
        context: Context dari RAG similarity search
        conversation_history: List of previous messages (optional)
    
    Returns:
        Complete prompt string untuk Ollama
    """
    
    # ✅ Build conversation history section
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        history_text = "\n\n=== RIWAYAT PERCAKAPAN (untuk memahami konteks) ===\n"
        
        # Ambil maksimal 10 messages terakhir (5 pairs) agar prompt tidak terlalu panjang
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                history_text += f"\nUSER: {content}"
            else:
                history_text += f"\nASSISTANT: {content}"
        
        history_text += "\n" + "=" * 60 + "\n"
    
    # ✅ Build complete prompt
    prompt = f"""Anda adalah asisten AI yang membantu menjawab pertanyaan tentang data SPK (Surat Perintah Kerja) dan jaringan telekomunikasi.

INSTRUKSI PENTING:
1. Jawab pertanyaan HANYA berdasarkan CONTEXT yang diberikan di bawah
2. PERHATIKAN riwayat percakapan untuk memahami konteks dan referensi seperti "nya", "itu", "tersebut", "dia", "ini"
3. Jika user bertanya dengan kata ganti (nya, itu, dll), rujuk ke entitas yang dibahas di riwayat percakapan sebelumnya
4. Jika informasi tidak ada di context atau riwayat, katakan "Informasi tidak tersedia dalam database"
5. Jawab dalam Bahasa Indonesia yang natural, jelas, dan to-the-point
6. Jika ada data teknis (nomor jaringan/nojar, nomor SPK, nama pelanggan, POP, vendor, teknisi, lokasi), sebutkan dengan jelas dan spesifik
7. Berikan jawaban yang langsung menjawab pertanyaan, tidak perlu penjelasan panjang lebar
8. Format jawaban dengan rapi, gunakan line break jika diperlukan untuk readability
9. JANGAN membuat asumsi atau menambahkan informasi yang tidak ada di context
{history_text}

=== CONTEXT DATA (Sumber informasi utama) ===
{context}
{"=" * 60}

PERTANYAAN USER SAAT INI:
{query}

JAWABAN (dalam Bahasa Indonesia, berdasarkan context dan riwayat percakapan):"""
    
    return prompt


# ============================================
# RUN APP
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Flask API Server Starting...")
    print("=" * 60)
    print(f"📍 Server URL: http://localhost:5000")
    print(f"🤖 Ollama URL: {OLLAMA_BASE_URL}")
    print(f"📊 Embedding Model: {EMBEDDING_MODEL}")
    print(f"💬 Chat Model: {CHAT_MODEL}")
    print("=" * 60)
    print("\n📋 Available Endpoints:")
    print("  POST /process-pdf          - Process PDF document")
    print("  POST /generate-embedding   - Generate text embedding")
    print("  POST /chat                 - Chat with RAG context + conversation memory")
    print("  GET  /health              - Health check")
    print("=" * 60)
    print("\n✨ NEW FEATURES:")
    print("  ✅ Conversation memory support")
    print("  ✅ Context-aware responses")
    print("  ✅ Enhanced prompt engineering")
    print("  ✅ Better error handling")
    print("=" * 60)
    print()
    
    app.run(port=5000, debug=True)