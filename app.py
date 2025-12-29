from flask import Flask, request, jsonify, Response, stream_with_context
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
CHAT_MODEL = "llama3.2:3b"

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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            pdf_path = tmp.name

        result = pengecekan_file(pdf_path)

        if not isinstance(result, dict):
            return jsonify({"error": "pengecekan_file must return JSON(dict)"}), 500

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
    """Generate embedding dari text menggunakan Ollama"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Text is required"}), 400
        
        text = data['text']
        model = data.get('model', EMBEDDING_MODEL)
        
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
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """Chat dengan Ollama (NON-STREAMING) - untuk RAG mode"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Query is required"}), 400
        
        query = data['query']
        context = data.get('context', '')
        conversation_history = data.get('conversation_history', [])
        model = data.get('model', CHAT_MODEL)
        
        prompt = build_rag_prompt(query, context, conversation_history)
        
        print("=" * 60)
        print("📨 CHAT REQUEST (NON-STREAMING)")
        print("=" * 60)
        print(f"Query: {query}")
        print(f"Has Context: {len(context) > 0}")
        print("=" * 60)
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 512,
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
        answer = result.get('response', '').strip()
        
        print("✅ CHAT RESPONSE GENERATED")
        print(f"Answer Length: {len(answer)} chars")
        print("=" * 60)
        print()
        
        return jsonify({
            "answer": answer,
            "model": model
        })
    
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================
# ✨ NEW: STREAMING CHAT ENDPOINT
# ============================================

@app.route('/chat-stream', methods=['POST'])
def chat_stream():
    """
    🔥 STREAMING chat dengan Ollama - Real-time token by token
    
    Request Body:
    {
        "query": "Pertanyaan user",
        "context": "Context dari RAG (optional)",
        "conversation_history": [...],  // optional
        "model": "llama3.2:3b"  // optional
    }
    
    Response: Server-Sent Events (SSE)
    data: {"token": "H"}
    data: {"token": "a"}
    data: {"token": "l"}
    data: {"token": "o"}
    data: {"done": true}
    """
    
    def generate():
        try:
            data = request.get_json()
            
            if not data or 'query' not in data:
                yield f"data: {json.dumps({'error': 'Query is required'})}\n\n"
                return
            
            query = data['query']
            context = data.get('context', '')
            conversation_history = data.get('conversation_history', [])
            model = data.get('model', CHAT_MODEL)
            
            # Build prompt
            prompt = build_rag_prompt(query, context, conversation_history)
            
            print("=" * 60)
            print("🌊 STREAMING CHAT REQUEST")
            print("=" * 60)
            print(f"Query: {query}")
            print(f"Has Context: {len(context) > 0}")
            print(f"Has History: {len(conversation_history) > 0}")
            print("=" * 60)
            
            # ✅ Call Ollama dengan stream=True
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,  # 🔥 Enable streaming
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 512,
                    }
                },
                stream=True,  # 🔥 Important: stream response
                timeout=300
            )
            
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code}"
                print(f"❌ {error_msg}")
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
            
            # ✅ Stream setiap token dari Ollama
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        
                        # Ollama mengirim response per token
                        if 'response' in chunk:
                            token = chunk['response']
                            full_response += token
                            
                            # 🔥 Kirim token langsung ke client
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        
                        # Check jika streaming selesai
                        if chunk.get('done', False):
                            print(f"✅ STREAMING COMPLETED")
                            print(f"Total Length: {len(full_response)} chars")
                            print("=" * 60)
                            print()
                            
                            # Kirim signal selesai
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                    
                    except json.JSONDecodeError:
                        # Skip invalid JSON
                        continue
        
        except requests.exceptions.Timeout:
            print("❌ Ollama request timeout")
            yield f"data: {json.dumps({'error': 'Request timeout'})}\n\n"
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Ollama connection error: {str(e)}")
            yield f"data: {json.dumps({'error': f'Connection error: {str(e)}'})}\n\n"
        
        except Exception as e:
            print(f"❌ Streaming error: {str(e)}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    # ✅ Return streaming response dengan SSE
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Connection': 'keep-alive'
        }
    )


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
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
    """Build prompt untuk RAG chatbot dengan conversation history"""
    
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        history_text = "\n\n=== RIWAYAT PERCAKAPAN ===\n"
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                history_text += f"\nUSER: {content}"
            else:
                history_text += f"\nASSISTANT: {content}"
        
        history_text += "\n" + "=" * 60 + "\n"
    
    prompt = f"""Anda adalah asisten AI yang membantu menjawab pertanyaan tentang data SPK dan jaringan telekomunikasi.

INSTRUKSI:
1. Jawab berdasarkan CONTEXT yang diberikan
2. Perhatikan riwayat percakapan untuk konteks
3. Jawab dalam Bahasa Indonesia yang natural
4. Sebutkan data teknis dengan jelas (nojar, SPK, pelanggan, POP, vendor, teknisi)
5. Format jawaban dengan rapi
{history_text}

=== CONTEXT DATA ===
{context}
{"=" * 60}

PERTANYAAN: {query}

JAWABAN:"""
    
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
    print("=" * 60)
    print("\n📋 Available Endpoints:")
    print("  POST /process-pdf          - Process PDF")
    print("  POST /generate-embedding   - Generate embedding")
    print("  POST /chat                 - Chat (NON-streaming)")
    print("  POST /chat-stream          - 🔥 Chat STREAMING (NEW)")
    print("  GET  /health              - Health check")
    print("=" * 60)
    print("\n✨ STREAMING FEATURES:")
    print("  🌊 Real-time token streaming")
    print("  ⚡ No waiting for complete response")
    print("  🎯 Server-Sent Events (SSE)")
    print("=" * 60)
    print()
    
    app.run(port=5000, debug=True, threaded=True)