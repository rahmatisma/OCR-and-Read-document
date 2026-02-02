from flask import Flask, request, jsonify, Response, stream_with_context
from validate_first_page import validate_first_page
import tempfile
import uuid
import requests
import json
import os
import hashlib
from collections import OrderedDict
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from main import pengecekan_file
from text_to_sql_generator import generate_sql_with_llm

app = Flask(__name__)

# ============================================
# KONFIGURASI
# ============================================
OLLAMA_BASE_URL = "http://localhost:11434"
# SESUDAH (VPS)
# OLLAMA_BASE_URL = " http://116.193.191.185:11434"
EMBEDDING_MODEL = "nomic-embed-text"
# CHAT_MODEL = "llama3.2:3b"
CHAT_MODEL = "llama3.1:8b"

# ============================================
# CACHE & SIMILARITY SYSTEM
# ============================================

# In-memory cache untuk classification (max 1000 entries)
classification_cache = OrderedDict()
MAX_CACHE_SIZE = 1000

# History untuk similarity matching
classification_history = []
MAX_HISTORY_SIZE = 500

def get_query_hash(query: str) -> str:
    """Generate hash untuk exact match caching"""
    normalized = query.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()

def add_to_cache(query: str, classification: dict):
    """Add classification to cache"""
    global classification_cache
    
    query_hash = get_query_hash(query)
    classification_cache[query_hash] = classification
    
    # LRU: Remove oldest if cache full
    if len(classification_cache) > MAX_CACHE_SIZE:
        classification_cache.popitem(last=False)
    
    print(f"💾 Cached classification for: {query[:50]}...")

def get_from_cache(query: str) -> dict:
    """Get classification from cache"""
    query_hash = get_query_hash(query)
    return classification_cache.get(query_hash)

def add_to_history(query: str, classification: dict, embedding: list):
    """Add to history for similarity matching"""
    global classification_history
    
    classification_history.append({
        'query': query,
        'classification': classification,
        'embedding': embedding
    })
    
    # Keep only recent history
    if len(classification_history) > MAX_HISTORY_SIZE:
        classification_history.pop(0)

def find_similar_query(query_embedding: list, threshold: float = 0.85) -> dict:
    """Find similar query in history"""
    if not classification_history:
        return None
    
    # Calculate similarities
    similarities = []
    for item in classification_history:
        sim = cosine_similarity(
            [query_embedding], 
            [item['embedding']]
        )[0][0]
        similarities.append((sim, item))
    
    # Get most similar
    best_match = max(similarities, key=lambda x: x[0])
    similarity_score, matched_item = best_match
    
    if similarity_score >= threshold:
        print(f" Similar query found (similarity: {similarity_score:.2f})")
        print(f"   Original: {matched_item['query'][:50]}...")
        return matched_item['classification']
    
    return None

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
            print(f" Laravel Storage Path: {laravel_storage_path}")
            
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
        print(f" Processing completed!")
        print(f"📊 Total dokumentasi: {len(result.get('dokumentasi', []))}")
        print(f"{'='*60}\n")

        return jsonify({
            "message": "processed ok",
            "filename": json_filename,
            "data": result
        })

    except Exception as e:
        print(f"\n{'='*60}")
        print(f" Error processing PDF: {str(e)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        # Cleanup temporary file
        try:
            if 'pdf_path' in locals():
                os.unlink(pdf_path)
                print(f"  Temporary PDF deleted")
        except:
            pass


# ============================================
# ENDPOINT: VALIDATE FIRST PAGE (UPDATED)
# ============================================
@app.route('/validate-first-page', methods=['POST'])
def validate_first_page_endpoint():
    """
     Endpoint untuk validasi cepat halaman pertama PDF.
    Digunakan sebelum full processing untuk deteksi jenis dokumen.
    
    Request:
        - file: PDF file (multipart/form-data)
        - expected_category: 'spk', 'checklist', atau 'pmpop' (optional)
    
    Response:
        {
            "success": true/false,
            "document_type": "spk_survey" / "checklist_wireless" / "form_pm_pop" / "unknown",
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

        print(f"[INFO]  Validating first page: {file.filename}")
        if expected_category:
            print(f"[INFO] Expected category: {expected_category}")

        # Jalankan validasi
        result = validate_first_page(pdf_path)

        # Jika expected_category diberikan, cek kesesuaian
        if expected_category:
            document_type = result.get('document_type', 'unknown')
            
            spk_types = ['spk_survey', 'spk_instalasi', 'spk_dismantle', 'spk_aktivasi']
            checklist_types = ['checklist_wireline', 'checklist_wireless']
            pmpop_types = [
                'form_pm_1phase_ups',
                'form_pm_3phase_ups',
                'form_pm_ac',
                'form_pm_inverter',
                'form_pm_ruang_shelter',
                'form_pm_rectifier',
                'form_pm_petir_grounding',
                'form_pm_instalasi_kabel',
                'form_pm_battery',
                'form_pm_pole_tower',
                'form_pm_dokumentasi_perangkat',
                'form_pm_genset',
                'form_pm_permohonan_tindak_lanjut',
                'form_pm_tindak_lanjut',
                'form_pm_jadwal_sentral',
            ]
            
            if expected_category == 'spk':
                is_valid = document_type in spk_types
            elif expected_category == 'checklist':
                is_valid = document_type in checklist_types
            elif expected_category == 'pmpop':
                is_valid = document_type in pmpop_types
            else:
                is_valid = False
            
            result['is_valid_for_category'] = is_valid
            
            #  UPDATE ERROR MESSAGES
            if not is_valid and result['success']:
                if expected_category == 'spk':
                    if document_type in checklist_types:
                        result['message'] = f"Dokumen ini adalah Form Checklist ({document_type}), bukan SPK!"
                    elif document_type in pmpop_types:
                        result['message'] = f"Dokumen ini adalah Form PM POP, bukan SPK!"
                
                elif expected_category == 'checklist':
                    if document_type in spk_types:
                        result['message'] = f"Dokumen ini adalah SPK ({document_type}), bukan Form Checklist!"
                    elif document_type in pmpop_types:
                        result['message'] = f"Dokumen ini adalah Form PM POP, bukan Form Checklist!"
                
                elif expected_category == 'pmpop':  #  BARU
                    if document_type in spk_types:
                        result['message'] = f"Dokumen ini adalah SPK ({document_type}), bukan Form PM POP!"
                    elif document_type in checklist_types:
                        result['message'] = f"Dokumen ini adalah Form Checklist ({document_type}), bukan Form PM POP!"

        print(f"[INFO]  Validation result: {result}")

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
            timeout=200
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
    """
    Chat dengan Ollama (NON-STREAMING)
    
    UPDATED: Support 'strict' mode untuk anti-hallucination
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Query is required"}), 400
        
        query = data['query']
        context = data.get('context', '')
        conversation_history = data.get('conversation_history', [])
        model = data.get('model', CHAT_MODEL)
        mode = data.get('mode', 'strict')  #  NEW: 'strict' or 'normal'
        
        #  Build prompt based on mode
        if mode == 'strict':
            prompt = build_strict_rag_prompt(query, context, conversation_history)
            print(f"🛡️  Using STRICT mode (anti-hallucination)")
        else:
            prompt = build_rag_prompt(query, context, conversation_history)
            print(f" Using NORMAL mode")
        
        print("=" * 60)
        print("📨 CHAT REQUEST (NON-STREAMING)")
        print("=" * 60)
        print(f"Query: {query}")
        print(f"Mode: {mode}")
        print(f"Has Context: {len(context) > 0}")
        print("=" * 60)
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  #  Very low = less creative = less hallucination
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.2,
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
        
        print(" CHAT RESPONSE GENERATED")
        print(f"Answer Length: {len(answer)} chars")
        print("=" * 60)
        print()
        
        return jsonify({
            "answer": answer,
            "model": model,
            "mode": mode
        })
    
    except Exception as e:
        print(f" Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat-stream', methods=['POST'])
def chat_stream():
    """🔥 STREAMING chat - UPDATED with strict mode support"""
    
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
            mode = data.get('mode', 'strict')  #  NEW
            
            #  Build prompt based on mode
            if mode == 'strict':
                prompt = build_strict_rag_prompt(query, context, conversation_history)
            else:
                prompt = build_rag_prompt(query, context, conversation_history)
            
            print("=" * 60)
            print("🌊 STREAMING CHAT REQUEST")
            print("=" * 60)
            print(f"Query: {query}")
            print(f"Mode: {mode}")
            print(f"Has Context: {len(context) > 0}")
            print("=" * 60)
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.1,  #  Low temp
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.2,
                        "num_predict": 512,
                    }
                },
                stream=True,
                timeout=300
            )
            
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code}"
                print(f" {error_msg}")
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
                            print(f" STREAMING COMPLETED")
                            print(f"Total Length: {len(full_response)} chars")
                            print("=" * 60)
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f" Streaming error: {str(e)}")
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

@app.route('/classify-intent', methods=['POST'])
def classify_intent():
    """
    🧠 SEMANTIC-AWARE Intent Classification
    
    FIXED: Proper context override when new entity is detected in query
    """
    try:
        data = request.get_json()
        query = data['query']
        context = data.get('context', {})
        history = data.get('conversation_history', [])
        
        #  Handle context type
        if isinstance(context, list):
            context = {}
        elif not isinstance(context, dict):
            context = {}
        
        print("=" * 60)
        print("🧠 SEMANTIC INTENT CLASSIFICATION")
        print("=" * 60)
        print(f"Query: {query}")
        print(f"Context (incoming): {context}")
        
        query_lower = query.lower().strip()
        
        #  Extract entities FROM QUERY (these OVERRIDE context!)
        import re
        
        extracted_nojar = None
        extracted_spk = None
        
        # Extract nojar (10 digits) from query
        nojar_match = re.search(r'\b(\d{10})\b', query)
        if nojar_match:
            extracted_nojar = nojar_match.group(1)
            print(f" Extracted nojar from query: {extracted_nojar}")
        
        # Extract SPK from query (various formats)
        spk_patterns = [
            r'spk\s+([0-9]{6}/[A-Z\-]+/\d{4})',  # Format: 065848/WO-LA/2021
            r'no\s+spk\s+([0-9]{6}/[A-Z\-]+/\d{4})',
            r'nomor\s+spk\s+([0-9]{6}/[A-Z\-]+/\d{4})',
            r'([0-9]{6}/[A-Z\-]+/\d{4})',  # Direct format
        ]
        
        for pattern in spk_patterns:
            spk_match = re.search(pattern, query, re.IGNORECASE)
            if spk_match:
                extracted_spk = spk_match.group(1)
                print(f" Extracted SPK from query: {extracted_spk}")
                break
        
        #  CRITICAL: Override context if new entity found in query
        if extracted_nojar:
            # New nojar in query → OVERRIDE old context
            if context.get('last_nojar') != extracted_nojar:
                print(f"⚠️  CONTEXT OVERRIDE: nojar {context.get('last_nojar')} → {extracted_nojar}")
                context['last_nojar'] = extracted_nojar
                # Clear related context when nojar changes
                context['last_spk'] = None
                context['last_pelanggan'] = None
        
        if extracted_spk:
            # New SPK in query → OVERRIDE old context
            if context.get('last_spk') != extracted_spk:
                print(f"⚠️  CONTEXT OVERRIDE: spk {context.get('last_spk')} → {extracted_spk}")
                context['last_spk'] = extracted_spk
        
        # Get final context values
        has_nojar = bool(context.get('last_nojar'))
        has_spk = bool(context.get('last_spk'))
        
        print(f" Final Context:")
        print(f"  - nojar: {context.get('last_nojar')}")
        print(f"  - spk: {context.get('last_spk')}")
        print(f"  - has_nojar: {has_nojar}, has_spk: {has_spk}")
        
        #  Analyze conversation history
        last_was_count = False
        last_was_about_spk = False
        
        if history and len(history) > 0:
            for msg in history[-4:]:
                content = msg.get('content', '').lower()
                
                if any(kw in content for kw in ['berapa', 'jumlah', 'ada', 'ditemukan', 'spk']):
                    last_was_about_spk = True
                    
                if any(kw in content for kw in ['ditemukan', 'ada ', ' spk']):
                    last_was_count = True
            
            print(f"📊 History analysis: last_was_count={last_was_count}, last_was_about_spk={last_was_about_spk}")
        
        # ================================================
        # 🔥 RULE 0: Ultra-short continuation queries
        # ================================================
        ultra_short_continuation = [
            'sebutkan', 'list', 'daftar', 'apa saja', 'apa saja?',
            'tunjukkan', 'show', 'detail', 'nya', 'tersebut',
            'berapa', 'ada berapa', 'siapa', 'kapan', 'dimana'
        ]
        
        is_ultra_short = len(query.split()) <= 2
        is_continuation_word = any(query_lower.startswith(kw) for kw in ultra_short_continuation)
        
        if is_ultra_short and is_continuation_word and (has_nojar or has_spk):
            print(" RULE MATCH: Ultra-short continuation → SQL")
            
            if query_lower in ['sebutkan', 'list', 'daftar', 'apa saja', 'apa saja?', 'tunjukkan', 'show']:
                query_type = 'LIST_SPK'
            elif query_lower in ['berapa', 'ada berapa']:
                query_type = 'COUNT_SPK'
            else:
                query_type = 'SPECIFIC_QUERY'
            
            return jsonify({
                'type': query_type,
                'strategy': 'SQL',
                'confidence': 0.98,
                'reasoning': 'Ultra-short continuation dengan context',
                'entities': {
                    'nojar': context.get('last_nojar'),
                    'spk': context.get('last_spk'),
                },
                'is_continuation': True,
                'rule_match': True
            })
        
        # ================================================
        # 🔥 RULE 0.5: Explicit SPK query (HIGH PRIORITY!)
        # ================================================
        if extracted_spk:
            # Query explicitly mentions SPK number
            print(" RULE MATCH: Explicit SPK query → SQL")
            
            # Determine query type
            if any(kw in query_lower for kw in ['vendor', 'teknisi']):
                query_type = 'GET_VENDOR_TEKNISI'
            elif any(kw in query_lower for kw in ['detail', 'data', 'tampilkan', 'info']):
                query_type = 'GET_SPK_DETAIL'
            else:
                query_type = 'SPECIFIC_QUERY'
            
            return jsonify({
                'type': query_type,
                'strategy': 'SQL',
                'confidence': 0.98,
                'reasoning': 'Explicit SPK number in query',
                'entities': {
                    'nojar': context.get('last_nojar'),
                    'spk': extracted_spk,  # Use extracted SPK!
                },
                'rule_match': True,
                'explicit_spk': True
            })
        
        # ================================================
        # RULE 1: Continuation after count query
        # ================================================
        if last_was_count and (has_nojar or has_spk):
            continuation_words = ['sebutkan', 'apa saja', 'list', 'daftar', 
                                'tunjukkan', 'detail', 'lihat', 'tampilkan']
            
            if any(kw in query_lower for kw in continuation_words):
                print(" RULE MATCH: Continuation after count → SQL (LIST)")
                return jsonify({
                    'type': 'LIST_SPK',
                    'strategy': 'SQL',
                    'confidence': 0.95,
                    'reasoning': 'List continuation after count query',
                    'entities': {
                        'nojar': context.get('last_nojar'),
                        'spk': context.get('last_spk'),
                    },
                    'is_continuation': True,
                    'expecting_list': True,
                    'rule_match': True
                })
        
        # ================================================
        # RULE 2: SPK queries dengan context
        # ================================================
        spk_keywords = ['spk', 'surat perintah', 'pekerjaan', 'no spk', 'nomor spk']
        count_keywords = ['berapa', 'jumlah', 'ada berapa', 'total', 'count']
        list_keywords = ['ada', 'adakah', 'apa saja', 'list', 'daftar', 'sebutkan']
        
        is_spk_query = any(kw in query_lower for kw in spk_keywords)
        is_count_query = any(kw in query_lower for kw in count_keywords)
        is_list_query = any(kw in query_lower for kw in list_keywords)
        
        if is_spk_query and has_nojar:
            if is_count_query:
                query_type = 'COUNT_SPK'
            elif is_list_query:
                query_type = 'LIST_SPK'
            else:
                query_type = 'SPECIFIC_QUERY'
            
            print(f" RULE MATCH: SPK query with context → SQL ({query_type})")
            return jsonify({
                'type': query_type,
                'strategy': 'SQL',
                'confidence': 0.95,
                'reasoning': 'SPK query dengan context nojar',
                'entities': {
                    'nojar': context.get('last_nojar'),
                    'spk': context.get('last_spk'),
                },
                'rule_match': True
            })
        
        # ================================================
        # RULE 3: Reference queries (tersebut, nya, itu)
        # ================================================
        reference_keywords = ['tersebut', 'itu', 'nya', 'tadi', 'diatas', 'terkait']
        is_reference_query = any(kw in query_lower for kw in reference_keywords)
        
        if is_reference_query and (has_nojar or has_spk):
            print(" RULE MATCH: Reference query → SQL")
            return jsonify({
                'type': 'SPECIFIC_QUERY',
                'strategy': 'SQL',
                'confidence': 0.9,
                'reasoning': 'Reference query dengan context',
                'entities': {
                    'nojar': context.get('last_nojar'),
                    'spk': context.get('last_spk'),
                },
                'rule_match': True
            })
        
        # ================================================
        # RULE 4: Specific questions dengan entity
        # ================================================
        specific_keywords = ['siapa', 'kapan', 'dimana', 'berapa', 'detail', 
                            'teknisi', 'vendor', 'pop', 'lokasi', 'pelanggan',
                            'tanggal', 'waktu', 'jasa', 'kecepatan', 'alamat']
        
        is_specific = any(kw in query_lower for kw in specific_keywords)
        
        if is_specific and (has_nojar or has_spk or extracted_nojar):
            print(" RULE MATCH: Specific query → SQL")
            return jsonify({
                'type': 'SPECIFIC_QUERY',
                'strategy': 'SQL',
                'confidence': 0.85,
                'reasoning': 'Specific question dengan entity',
                'entities': {
                    'nojar': context.get('last_nojar'),
                    'spk': context.get('last_spk'),
                },
                'rule_match': True
            })
        
        # ================================================
        # RULE 5: Explanation queries → RAG
        # ================================================
        explanation_keywords = ['jelaskan', 'bagaimana', 'mengapa', 'apa itu', 
                               'cara', 'prosedur', 'proses', 'kenapa', 'gimana']
        
        is_explanation = any(kw in query_lower for kw in explanation_keywords)
        
        if is_explanation:
            print(" RULE MATCH: Explanation query → RAG")
            return jsonify({
                'type': 'GENERAL_INFO',
                'strategy': 'RAG',
                'confidence': 0.9,
                'reasoning': 'Explanation/general query',
                'entities': {
                    'nojar': context.get('last_nojar'),
                    'spk': context.get('last_spk'),
                },
                'rule_match': True
            })
        
        # ================================================
        # DEFAULT: RAG (safe fallback)
        # ================================================
        print("⚠️  No rule match, defaulting to RAG")
        return jsonify({
            'type': 'GENERAL_INFO',
            'strategy': 'RAG',
            'confidence': 0.7,
            'reasoning': 'No specific rule matched, safe fallback',
            'entities': {
                'nojar': context.get('last_nojar'),
                'spk': context.get('last_spk'),
            },
            'rule_match': False
        })
        
    except Exception as e:
        print(f" Classification error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'type': 'GENERAL_INFO',
            'strategy': 'RAG',
            'confidence': 0.5,
            'reasoning': f'Error fallback: {str(e)}',
            'error': True,
            'entities': {'nojar': None, 'spk': None}
        }), 200

@app.route('/classification-stats', methods=['GET'])
def classification_stats():
    """Statistics untuk monitoring performance"""
    total_in_history = len(classification_history)
    cache_size = len(classification_cache)
    
    return jsonify({
        'cache': {
            'size': cache_size,
            'max_size': MAX_CACHE_SIZE,
            'usage_percent': round(cache_size / MAX_CACHE_SIZE * 100, 2)
        },
        'history': {
            'size': total_in_history,
            'max_size': MAX_HISTORY_SIZE,
            'usage_percent': round(total_in_history / MAX_HISTORY_SIZE * 100, 2)
        },
        'info': 'Query pertama: ~3s (LLM), Query serupa: ~0.1s (similarity), Query sama: ~0.001s (cache)'
    })

@app.route('/clear-classification-cache', methods=['POST'])
def clear_cache():
    """Clear cache (untuk development)"""
    global classification_cache, classification_history
    
    old_cache_size = len(classification_cache)
    old_history_size = len(classification_history)
    
    classification_cache.clear()
    classification_history.clear()
    
    return jsonify({
        'message': 'Cache cleared',
        'cleared': {
            'cache': old_cache_size,
            'history': old_history_size
        }
    })

from text_to_sql_generator import generate_sql_with_llm

@app.route('/generate-sql', methods=['POST'])
def generate_sql():
    """
    🎯 SMART HYBRID SQL GENERATION
    
    Tier 1: Pattern matching untuk simple queries (FAST)
    Tier 2: LLM generation untuk complex queries (SMART)
    
    Decision logic:
    - Cek pattern match dengan STRICT rules
    - Jika pattern TIDAK confident → LLM
    - Jika pattern match tapi result salah → LLM retry
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Query is required"}), 400
        
        query = data['query']
        intent = data.get('intent', {})
        context = data.get('context', {})
        
        if isinstance(context, list):
            context = {}
        elif not isinstance(context, dict):
            context = {}
        
        print("=" * 60)
        print("🎯 SMART HYBRID SQL GENERATION")
        print("=" * 60)
        print(f"Query: {query}")
        print(f"Context: {context}")
        print("=" * 60)
        
        # Extract entities dari query
        import re
        query_lower = query.lower()
        
        nojar = context.get('last_nojar', '')
        spk = context.get('last_spk', '')
        pelanggan = context.get('last_pelanggan', '')
        
        # Extract dari query (OVERRIDE context)
        nojar_match = re.search(r'\b(\d{10})\b', query)
        if nojar_match:
            nojar = nojar_match.group(1)
            print(f" Extracted nojar: {nojar}")
        
        spk_match = re.search(r'(\d{6}/[A-Z\-]+/\d{4})', query, re.IGNORECASE)
        if spk_match:
            spk = spk_match.group(1)
            print(f" Extracted SPK: {spk}")
        
        print(f" Final context: nojar={nojar}, spk={spk}")
        
        # ==========================================
        # 🤖 DECISION LOGIC: Pattern or LLM?
        # ==========================================
        
        use_llm = False
        reason = ""
        
        # Rule 1: Reference words → LLM (KECUALI simple queries)
        reference_words = ['tersebut', 'itu', 'tadi', 'yang tadi']
        has_reference = any(word in query_lower for word in reference_words)

        #  Exception: "berapa spk" queries tetap pakai pattern meski ada "tersebut"
        simple_count_with_ref = (
            'berapa' in query_lower and 
            'spk' in query_lower and
            has_reference and
            (nojar or spk)
        )

        if has_reference and not simple_count_with_ref:
            use_llm = True
            reason = "Query uses reference words (butuh context understanding)"
        
        # Rule 2: Complex questions → LLM
        complex_indicators = [
            'bagaimana', 'mengapa', 'jelaskan', 'bandingkan',
            'perbedaan', 'hubungan', 'analisis'
        ]
        if any(word in query_lower for word in complex_indicators):
            use_llm = True
            reason = "Complex question detected"
        
        # Rule 3: Ambiguous queries → LLM
        # "pop nya apa?" tanpa jelas refer ke apa
        ambiguous_patterns = [
            r'^(pop|teknisi|vendor|lokasi|alamat)\s+(nya|apa)\??$',
            r'^(siapa|kapan|dimana)\s+\w+\??$',
        ]
        for pattern in ambiguous_patterns:
            if re.match(pattern, query_lower.strip()):
                use_llm = True
                reason = "Ambiguous query needs context resolution"
                break
        
        # Rule 4: Multi-table joins → LLM (complex)
        needs_complex_join = (
            ('teknisi' in query_lower or 'vendor' in query_lower) and
            'spk' not in query_lower and
            spk  # Ada SPK context tapi query ga sebut SPK
        )
        if needs_complex_join:
            use_llm = True
            reason = "Needs complex JOIN logic"
        
        # Rule 5: NO CONTEXT → LLM (unless very simple)
        if not nojar and not spk and not pelanggan:
            simple_standalone = ['halo', 'hai', 'help', 'apa itu']
            if not any(word in query_lower for word in simple_standalone):
                use_llm = True
                reason = "No context available, needs smart interpretation"
        
        # ==========================================
        # 🚀 TIER 1: PATTERN-BASED (Simple & Fast)
        # ==========================================
        
        sql_query = ""
        generation_method = "unknown"
        
        if not use_llm:
            print("\n⚡ Trying PATTERN-BASED generation...")
            
            # Pattern 1: Count SPK (SIMPLE)
            if 'berapa' in query_lower and 'spk' in query_lower and nojar:
                print(" PATTERN: Count SPK")
                sql_query = f"""
                    SELECT COUNT(DISTINCT s.id_spk) as jumlah_spk
                    FROM spk s
                    WHERE s.no_jaringan = '{nojar}'
                    AND s.is_deleted = 0
                """
                generation_method = "pattern"
            
            # Pattern 2: List SPK (SIMPLE)
            elif ('spk' in query_lower or 'sebutkan' in query_lower or 'list' in query_lower) and nojar:
                # Check jenis filter
                jenis_map = {
                    'survey': 'survey',
                    'instalasi': 'instalasi',
                    'aktivasi': 'aktivasi',
                    'dismantle': 'dismantle',
                    'maintenance': 'maintenance'
                }
                
                jenis_filter = None
                for keyword, jenis in jenis_map.items():
                    if keyword in query_lower:
                        jenis_filter = jenis
                        break
                
                print(f" PATTERN: List SPK (jenis={jenis_filter or 'all'})")
                
                if jenis_filter:
                    sql_query = f"""
                        SELECT s.no_spk, s.jenis_spk, s.tanggal_spk, s.no_jaringan
                        FROM spk s
                        WHERE s.no_jaringan = '{nojar}'
                        AND s.jenis_spk = '{jenis_filter}'
                        AND s.is_deleted = 0
                        ORDER BY s.tanggal_spk DESC
                    """
                else:
                    sql_query = f"""
                        SELECT s.no_spk, s.jenis_spk, s.tanggal_spk, s.no_jaringan
                        FROM spk s
                        WHERE s.no_jaringan = '{nojar}'
                        AND s.is_deleted = 0
                        ORDER BY s.tanggal_spk DESC
                    """
                generation_method = "pattern"
            
            # Pattern 3: Pelanggan info (SIMPLE)
            elif 'pelanggan' in query_lower and nojar and 'apa' in query_lower:
                print(" PATTERN: Pelanggan info")
                sql_query = f"""
                    SELECT 
                        j.nama_pelanggan, 
                        j.lokasi_pelanggan,
                        j.no_jaringan,
                        j.jasa,
                        j.kecepatan
                    FROM jaringan j
                    WHERE j.no_jaringan = '{nojar}'
                    AND j.is_deleted = 0
                """
                generation_method = "pattern"
            
            # Pattern 4: Tanggal aktivasi (SIMPLE)
            elif 'kapan' in query_lower and ('aktivasi' in query_lower or 'survey' in query_lower or 'instalasi' in query_lower):
                jenis = 'aktivasi'
                if 'survey' in query_lower:
                    jenis = 'survey'
                elif 'instalasi' in query_lower:
                    jenis = 'instalasi'
                
                print(f" PATTERN: Kapan {jenis}")
                
                if nojar:
                    sql_query = f"""
                        SELECT s.no_spk, s.jenis_spk, s.tanggal_spk, s.no_jaringan,
                               j.nama_pelanggan,
                               sei.teknisi, sei.nama_vendor
                        FROM spk s
                        JOIN jaringan j ON s.no_jaringan = j.no_jaringan
                        LEFT JOIN spk_execution_info sei ON s.id_spk = sei.id_spk
                        WHERE s.no_jaringan = '{nojar}'
                        AND s.jenis_spk = '{jenis}'
                        AND s.is_deleted = 0
                        ORDER BY s.tanggal_spk DESC
                        LIMIT 1
                    """
                    generation_method = "pattern"
        
        # ==========================================
        # 🤖 TIER 2: LLM-POWERED (Complex & Smart)
        # ==========================================
        
        if not sql_query or use_llm:
            if not sql_query:
                reason = "No pattern match found"
            
            print(f"\n🤖 Using LLM generation: {reason}")
            print("=" * 60)
            
            # Update context untuk LLM
            llm_context = {
                'last_nojar': nojar,
                'last_spk': spk,
                'last_pelanggan': pelanggan
            }
            
            # Call LLM
            llm_result = generate_sql_with_llm(
                query=query,
                context=llm_context,
                ollama_url=OLLAMA_BASE_URL,
                model=CHAT_MODEL
            )
            
            if llm_result['success']:
                sql_query = llm_result['sql']
                generation_method = "llm"
                print(f" LLM generated SQL successfully")
            else:
                print(f" LLM generation failed: {llm_result.get('error')}")
                
                # Emergency fallback
                if nojar:
                    print(" Emergency fallback: default jaringan query")
                    sql_query = f"""
                        SELECT j.*
                        FROM jaringan j
                        WHERE j.no_jaringan = '{nojar}'
                        AND j.is_deleted = 0
                    """
                    generation_method = "fallback"
                else:
                    return jsonify({
                        "success": False,
                        "error": f"Cannot generate SQL: {llm_result.get('error')}",
                        "reason": "No pattern match and LLM failed"
                    }), 400
        
        # ==========================================
        #  RETURN RESULT
        # ==========================================
        
        print(f"\n✅ SQL Generated ({generation_method}):")
        print(sql_query.strip())
        print("=" * 60)
        print()
        
        return jsonify({
            'success': True,
            'sql': sql_query.strip(),
            'generation_method': generation_method,
            'confidence': 0.95 if generation_method == "pattern" else 0.85,
            'reason': reason if generation_method == "llm" else "Pattern matched"
        }), 200
    
    except Exception as e:
        print(f" SQL generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=60)
        
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
    """Build prompt untuk RAG chatbot dengan FULL context awareness"""
    
    #  Build conversation history (ambil 5 terakhir)
    history_text = ""
    last_discussed_entities = {
        'nojar': None,
        'pelanggan': None,
        'spk': None
    }
    
    if conversation_history and len(conversation_history) > 0:
        history_text = "\n\n=== PERCAKAPAN SEBELUMNYA ===\n"
        recent_history = conversation_history[-5:]  # 5 exchange terakhir
        
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                history_text += f"\nUser: {content}"
            else:
                history_text += f"\nAssistant: {content}"
                
                #  Extract entities dari jawaban sebelumnya
                import re
                
                # Extract nojar (10 digit)
                nojar_match = re.search(r'\b(\d{10})\b', content)
                if nojar_match:
                    last_discussed_entities['nojar'] = nojar_match.group(1)
                
                # Extract pelanggan (kata setelah "pelanggan")
                pelanggan_match = re.search(r'pelanggan\s+([A-Z][A-Z\s&\.]{5,})', content, re.IGNORECASE)
                if pelanggan_match:
                    last_discussed_entities['pelanggan'] = pelanggan_match.group(1).strip()
                
                # Extract SPK
                spk_match = re.search(r'SPK[:\s]+([A-Z0-9\/\-]+)', content, re.IGNORECASE)
                if spk_match:
                    last_discussed_entities['spk'] = spk_match.group(1)
        
        history_text += "\n" + "=" * 60 + "\n"
    
    #  Build entity context summary
    entity_context = ""
    if any(last_discussed_entities.values()):
        entity_context = "\n=== TOPIK YANG SEDANG DIBAHAS ===\n"
        if last_discussed_entities['nojar']:
            entity_context += f"Nomor Jaringan yang sedang dibahas: {last_discussed_entities['nojar']}\n"
        if last_discussed_entities['pelanggan']:
            entity_context += f"Pelanggan yang sedang dibahas: {last_discussed_entities['pelanggan']}\n"
        if last_discussed_entities['spk']:
            entity_context += f"SPK yang sedang dibahas: {last_discussed_entities['spk']}\n"
        entity_context += "=" * 60 + "\n"
    
    #  PROMPT dengan FULL CONTEXT AWARENESS
    prompt = f"""Anda adalah asisten database SPK Management System PT. Lintasarta.

ATURAN MUTLAK:
1. HANYA jawab dari DATA di bawah
2. DILARANG mengarang nama perusahaan atau data apapun
3. Jika DATA kosong → jawab "Data tidak ditemukan"
4. Jika pertanyaan singkat (misal: "berapa spk?", "pop nya?", "ada instalasi?"):
   - LIHAT PERCAKAPAN SEBELUMNYA untuk tahu topik yang sedang dibahas
   - Gunakan konteks nomor jaringan/SPK yang baru saja dibahas
   - Jawab sesuai topik tersebut
{history_text}{entity_context}

=== DATA DARI DATABASE ===
{context if context and len(context.strip()) > 50 else "TIDAK ADA DATA RELEVAN"}
{"=" * 60}

PERTANYAAN USER: {query}

CARA MENJAWAB:
- Jika pertanyaan singkat ("berapa spk?", "pop nya?"), gunakan konteks dari percakapan sebelumnya
- Jika pertanyaan jelas menyebut nomor jaringan/SPK baru, fokus ke yang baru
- Jawab natural tanpa menyebut "berdasarkan percakapan sebelumnya"

JAWABAN (dari DATA + KONTEKS):"""
    
    return prompt

def build_strict_rag_prompt(query: str, context: str, conversation_history: list = None) -> str:
    """
    🛡️ STRICT PROMPT - Anti-Hallucination Mode
    
    Memaksa LLM untuk:
    1. HANYA pakai data dari context
    2. TIDAK mengarang nama/nomor/tanggal
    3. Bilang "tidak ditemukan" jika data kosong
    """
    
    # Build history
    history_text = ""
    last_discussed_entities = {
        'nojar': None,
        'pelanggan': None,
        'spk': None
    }
    
    if conversation_history and len(conversation_history) > 0:
        history_text = "\n\n=== PERCAKAPAN SEBELUMNYA ===\n"
        recent_history = conversation_history[-5:]
        
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                history_text += f"\nUser: {content}"
            else:
                history_text += f"\nAssistant: {content}"
                
                # Extract entities dari history
                import re
                
                nojar_match = re.search(r'\b(\d{10})\b', content)
                if nojar_match:
                    last_discussed_entities['nojar'] = nojar_match.group(1)
                
                pelanggan_match = re.search(r'pelanggan\s+([A-Z][A-Z\s&\.]{5,})', content, re.IGNORECASE)
                if pelanggan_match:
                    last_discussed_entities['pelanggan'] = pelanggan_match.group(1).strip()
                
                spk_match = re.search(r'SPK[:\s]+([A-Z0-9\/\-]+)', content, re.IGNORECASE)
                if spk_match:
                    last_discussed_entities['spk'] = spk_match.group(1)
        
        history_text += "\n" + "=" * 60 + "\n"
    
    # Build entity context
    entity_context = ""
    if any(last_discussed_entities.values()):
        entity_context = "\n=== TOPIK YANG SEDANG DIBAHAS ===\n"
        if last_discussed_entities['nojar']:
            entity_context += f"Nomor Jaringan: {last_discussed_entities['nojar']}\n"
        if last_discussed_entities['pelanggan']:
            entity_context += f"Pelanggan: {last_discussed_entities['pelanggan']}\n"
        if last_discussed_entities['spk']:
            entity_context += f"SPK: {last_discussed_entities['spk']}\n"
        entity_context += "=" * 60 + "\n"
    
    # Check if context has meaningful data
    has_data = (
        context and 
        context.strip() and 
        context != "Tidak ada data relevan." and
        len(context) > 100  # Minimum meaningful context
    )
    
    if not has_data:
        # ⚠️ NO DATA PROMPT - Force LLM to say "no data"
        prompt = f"""Anda adalah asisten database SPK Management System PT. Lintasarta.

{history_text}{entity_context}

PERTANYAAN USER: "{query}"

⚠️ CRITICAL: TIDAK ADA DATA RELEVAN YANG DITEMUKAN DI DATABASE.

🛡️ ATURAN WAJIB (ZERO TOLERANCE):
1.  JANGAN membuat data sendiri (no_jaringan, no_spk, nama, tanggal, angka)
2.  JANGAN menebak atau mengira-ngira
3.  JANGAN memberikan informasi umum yang tidak relevan
4.  WAJIB jawab: "Tidak ditemukan data yang sesuai dengan pertanyaan Anda"
5.  Sarankan user untuk:
   - Cek kembali nomor jaringan/SPK yang ditanyakan
   - Gunakan keyword yang lebih spesifik
   - Pastikan data sudah ada di sistem

CONTOH JAWABAN YANG BENAR:
"Maaf, tidak ditemukan data untuk nomor jaringan yang Anda maksud. Silakan periksa kembali nomor jaringan atau gunakan keyword yang lebih spesifik."

RESPONS ANDA (sesuai aturan di atas):"""
    
    else:
        #  HAS DATA PROMPT - Force LLM to ONLY use context
        prompt = f"""Anda adalah asisten database SPK Management System PT. Lintasarta.

{history_text}{entity_context}

=== DATA DARI DATABASE ===
{context}
{"=" * 60}

PERTANYAAN USER: "{query}"

🛡️ ATURAN KETAT (ZERO TOLERANCE FOR HALLUCINATION):

WAJIB DILAKUKAN:
1.  HANYA jawab berdasarkan DATA DI ATAS
2.  Sebutkan angka/nomor/tanggal EXACT dari data (jangan bulatkan!)
3.  Jika data tidak lengkap, katakan "Data tidak tersedia untuk [X]"
4.  Gunakan format yang jelas (bold dengan **X** untuk penting)
5.  Sebutkan sumber: "Berdasarkan data..." atau "Data menunjukkan..."
6.  Jika pertanyaan singkat, gunakan konteks dari percakapan sebelumnya

DILARANG KERAS:
1.  JANGAN tambahkan informasi dari pengetahuan umum Anda
2.  JANGAN menebak atau membuat nomor/tanggal/nama sendiri
3.  JANGAN asumsikan data yang tidak ada di context
4.  JANGAN pakai kata "kemungkinan", "biasanya", "sekitar" (harus EXACT!)
5.  JANGAN buat kesimpulan yang tidak didukung data

FORMAT JAWABAN:
- Untuk "berapa": Sebutkan angka EXACT dari data
- Untuk "siapa": Sebutkan nama EXACT dari data
- Untuk "kapan": Sebutkan tanggal EXACT dari data
- Untuk list: Gunakan numbered list (1., 2., 3.)
- Untuk detail: Struktur yang jelas dengan bullet/paragraf

CONTOH JAWABAN YANG BENAR:
Query: "Berapa SPK untuk nojar 2023390898?"
 SALAH: "Terdapat beberapa SPK" (tidak exact!)
 BENAR: "Ditemukan **1 SPK** untuk nomor jaringan **2023390898**"

Query: "Siapa teknisi yang handle?"
 SALAH: "Teknisi yang biasanya..." (menebak!)
 BENAR: "Teknisi yang menangani adalah **Firman Gustomi** dari vendor **DS3**"

Query: "Pop nya apa?"
 SALAH: "POP untuk jaringan ini adalah..." (tidak jelas rujukan!)
 BENAR: "POP untuk nomor jaringan **2023390898** adalah **JKTRMCSR01**"

JIKA DATA TIDAK ADA:
Query: "Berapa biaya instalasi?"
 SALAH: "Biaya biasanya sekitar..." (menebak!)
 BENAR: "Informasi biaya instalasi tidak tersedia dalam data"

RESPONS ANDA (HANYA dari DATA di atas, format natural Bahasa Indonesia):"""

    return prompt

@app.route('/evaluate-pdf', methods=['POST'])
def evaluate_pdf():
    """
    Endpoint untuk evaluasi PDF dengan ground truth
    
    Form Data:
        - file: PDF file
        - ground_truth_name: nama file ground truth (tanpa .json)
    
    Response:
        {
            "processing_result": {...},
            "evaluation": {
                "accuracy": 85.5,
                "total_fields": 8,
                "correct": 7,
                "incorrect": 1,
                "details": {...}
            }
        }
    """
    file = request.files.get("file")
    gt_name = request.form.get("ground_truth_name")
    
    if not file:
        return jsonify({"error": "File not provided"}), 400
    
    if not gt_name:
        return jsonify({"error": "Ground truth name not provided"}), 400

    try:
        # Simpan file temporary
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            pdf_path = tmp.name

        print(f"\n{'='*60}")
        print(f"🧪 EVALUATION MODE")
        print(f"📄 PDF: {file.filename}")
        print(f"📋 Ground Truth: {gt_name}")
        print(f"{'='*60}\n")

        # Process PDF
        result = pengecekan_file(pdf_path)
        
        # Load ground truth
        from main import load_ground_truth, calculate_field_accuracy
        
        ground_truth = load_ground_truth(gt_name)
        
        if not ground_truth:
            return jsonify({
                "error": f"Ground truth file '{gt_name}_ground_truth.json' not found"
            }), 404
        
        # Evaluate
        evaluation = calculate_field_accuracy(ground_truth, result)
        
        print(f"\n{'='*60}")
        print(f"📊 EVALUATION RESULTS")
        print(f"{'='*60}")
        print(f" Correct: {evaluation['correct']}/{evaluation['total_fields']}")
        print(f"📈 Accuracy: {evaluation['accuracy']}%")
        print(f"{'='*60}\n")

        return jsonify({
            "message": "Evaluation completed",
            "processing_result": result,
            "evaluation": evaluation
        })

    except Exception as e:
        print(f"\n❌ Evaluation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    finally:
        try:
            if 'pdf_path' in locals():
                os.unlink(pdf_path)
        except:
            pass


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
    print("   Support Laravel storage path")
    print("  🗂️  Organized folder structure by document type")
    print("   Automatic path conversion to relative")
    print("=" * 60)
    print()
    
    app.run(port=5000, debug=True, threaded=True)