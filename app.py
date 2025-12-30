from flask import Flask, request, jsonify, Response, stream_with_context
from validate_first_page import validate_first_page
import tempfile
import uuid
import requests
import json
import os
from main import pengecekan_file

app = Flask(__name__)

# ============================================
# KONFIGURASI
# ============================================
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2:3b"

# ============================================
# ENDPOINT: PROCESS PDF (UPDATED)
# ============================================
@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    """
    Endpoint untuk process PDF dengan Laravel storage path
    
    Form Data:
        - file: PDF file (required)
        - laravel_storage_path: Path ke storage/app/public Laravel (optional)
    
    Response:
        {
            "message": "processed ok",
            "filename": "uuid.json",
            "data": {
                "dokumentasi": [...],
                "parsed": {...}
            }
        }
    """
    file = request.files.get("file")
    laravel_storage_path = request.form.get("laravel_storage_path")
    
    if not file:
        return jsonify({"error": "File not provided"}), 400

    try:
        # Simpan file temporary
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            pdf_path = tmp.name

        print(f"\n{'='*60}")
        print(f"📄 Processing PDF: {file.filename}")
        if laravel_storage_path:
            print(f"📁 Laravel Storage Path: {laravel_storage_path}")
            
            # Validasi path exists
            if not os.path.exists(laravel_storage_path):
                print(f"⚠️  WARNING: Laravel storage path tidak ditemukan!")
                print(f"   Path: {laravel_storage_path}")
                print(f"   Akan menggunakan folder 'output' default")
                laravel_storage_path = None
        print(f"{'='*60}\n")

        # Panggil pengecekan_file dengan laravel_storage_path
        result = pengecekan_file(pdf_path, laravel_storage_path=laravel_storage_path)

        if not isinstance(result, dict):
            return jsonify({"error": "pengecekan_file must return JSON(dict)"}), 500

        json_filename = f"{uuid.uuid4()}.json"

        print(f"\n{'='*60}")
        print(f"✅ Processing completed!")
        print(f"📊 Total dokumentasi: {len(result.get('dokumentasi', []))}")
        print(f"{'='*60}\n")

        return jsonify({
            "message": "processed ok",
            "filename": json_filename,
            "data": result
        })

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ Error processing PDF: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Cleanup temporary file
        try:
            if 'pdf_path' in locals():
                os.unlink(pdf_path)
                print(f"🗑️  Temporary PDF deleted")
        except:
            pass


# ============================================
# ENDPOINT: VALIDATE FIRST PAGE
# ============================================
@app.route('/validate-first-page', methods=['POST'])
def validate_first_page_endpoint():
    """
    🔍 Endpoint untuk validasi cepat halaman pertama PDF.
    Digunakan sebelum full processing untuk deteksi jenis dokumen.
    
    Request:
        - file: PDF file (multipart/form-data)
        - expected_category: 'spk' atau 'checklist' (optional)
    
    Response:
        {
            "success": true/false,
            "document_type": "spk_survey" / "checklist_wireless" / "unknown",
            "confidence": "high" / "medium" / "low",
            "message": "...",
            "is_valid_for_category": true/false
        }
    """
    file = request.files.get("file")
    expected_category = request.form.get("expected_category")
    
    if not file:
        return jsonify({"error": "File not provided"}), 400

    try:
        # Simpan file temporary
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            pdf_path = tmp.name

        print(f"[INFO] 🔍 Validating first page: {file.filename}")
        if expected_category:
            print(f"[INFO] Expected category: {expected_category}")

        # Jalankan validasi
        result = validate_first_page(pdf_path)

        # Jika expected_category diberikan, cek kesesuaian
        if expected_category:
            document_type = result.get('document_type', 'unknown')
            
            spk_types = ['spk_survey', 'spk_instalasi', 'spk_dismantle', 'spk_aktivasi']
            checklist_types = ['checklist_wireline', 'checklist_wireless']
            
            if expected_category == 'spk':
                is_valid = document_type in spk_types
            elif expected_category == 'checklist':
                is_valid = document_type in checklist_types
            else:
                is_valid = False
            
            result['is_valid_for_category'] = is_valid
            
            if not is_valid and result['success']:
                if expected_category == 'spk' and document_type in checklist_types:
                    result['message'] = f"Dokumen ini adalah Form Checklist ({document_type}), bukan SPK!"
                elif expected_category == 'checklist' and document_type in spk_types:
                    result['message'] = f"Dokumen ini adalah SPK ({document_type}), bukan Form Checklist!"

        print(f"[INFO] ✅ Validation result: {result}")

        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        print(f"[ERROR] Validation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Terjadi kesalahan saat validasi dokumen"
        }), 500

    finally:
        # Cleanup temporary file
        try:
            if 'pdf_path' in locals():
                os.unlink(pdf_path)
        except:
            pass


# ============================================
# RAG ENDPOINTS (unchanged)
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


@app.route('/chat-stream', methods=['POST'])
def chat_stream():
    """🔥 STREAMING chat dengan Ollama - Real-time token by token"""
    
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
            
            prompt = build_rag_prompt(query, context, conversation_history)
            
            print("=" * 60)
            print("🌊 STREAMING CHAT REQUEST")
            print("=" * 60)
            print(f"Query: {query}")
            print(f"Has Context: {len(context) > 0}")
            print("=" * 60)
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 512,
                    }
                },
                stream=True,
                timeout=300
            )
            
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code}"
                print(f"❌ {error_msg}")
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        
                        if 'response' in chunk:
                            token = chunk['response']
                            full_response += token
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        
                        if chunk.get('done', False):
                            print(f"✅ STREAMING COMPLETED")
                            print(f"Total Length: {len(full_response)} chars")
                            print("=" * 60)
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"❌ Streaming error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
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


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Flask API Server Starting...")
    print("=" * 60)
    print(f"📍 Server URL: http://localhost:5000")
    print(f"🤖 Ollama URL: {OLLAMA_BASE_URL}")
    print("=" * 60)
    print("\n📋 Available Endpoints:")
    print("  POST /process-pdf          - Process PDF (✨ UPDATED)")
    print("  POST /validate-first-page  - Validate PDF (QUICK)")
    print("  POST /generate-embedding   - Generate embedding")
    print("  POST /chat                 - Chat (NON-streaming)")
    print("  POST /chat-stream          - Chat STREAMING")
    print("  GET  /health              - Health check")
    print("=" * 60)
    print("\n✨ NEW FEATURES:")
    print("  📁 Support Laravel storage path")
    print("  🗂️  Organized folder structure by document type")
    print("  🔄 Automatic path conversion to relative")
    print("=" * 60)
    print()
    
    app.run(port=5000, debug=True, threaded=True)