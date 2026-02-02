"""
🛡️ STRICT PROMPT TEMPLATE - Zero Tolerance for Hallucination
"""

def build_strict_rag_prompt(query: str, context: str, conversation_history: list = None) -> str:
    """
    Build ultra-strict prompt that FORCES LLM to only use provided data
    """
    
    history_str = ""
    if conversation_history:
        history_str = "\n=== RIWAYAT PERCAKAPAN ===\n"
        for msg in conversation_history[-3:]:  # Last 3 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_str += f"{role.upper()}: {content}\n"
    
    # Check if context is empty
    has_data = context and context.strip() and context != "Tidak ada data relevan."
    
    if not has_data:
        # NO DATA PROMPT - Force LLM to say "no data found"
        prompt = f"""Anda adalah asisten chatbot untuk SPK Management System.

{history_str}

PERTANYAAN USER: "{query}"

⚠️ CRITICAL: TIDAK ADA DATA RELEVAN YANG DITEMUKAN DI DATABASE.

ATURAN WAJIB:
1.  JANGAN membuat data sendiri
2.  JANGAN menebak atau mengira-ngira
3.  JANGAN memberikan informasi umum yang tidak terkait
4.  WAJIB jawab: "Tidak ditemukan data yang sesuai dengan pertanyaan Anda."
5.  Sarankan user untuk:
   - Cek kembali nomor jaringan/SPK
   - Gunakan keyword yang lebih spesifik
   - Pastikan data sudah ter-upload

RESPONS ANDA:"""
    
    else:
        # HAS DATA PROMPT - Force LLM to ONLY use provided context
        prompt = f"""Anda adalah asisten chatbot untuk SPK Management System.

{history_str}

PERTANYAAN USER: "{query}"

{context}

🛡️ ATURAN KETAT (ZERO TOLERANCE):
1.  HANYA jawab berdasarkan DATA DI ATAS
2.  JANGAN tambahkan informasi dari pengetahuan umum Anda
3.  JANGAN menebak atau membuat nomor/tanggal/nama sendiri
4.  JANGAN asumsikan data yang tidak tertulis di context
5.  Jika data tidak lengkap, katakan "Data tidak tersedia untuk [X]"
6.  Sebutkan sumber data (misal: "Berdasarkan data SPK...")
7.  Gunakan format yang jelas dan mudah dibaca
8.  Jika user tanya detail yang tidak ada di context, jawab "Informasi tersebut tidak tersedia dalam data yang saya akses"

FORMAT JAWABAN:
- Untuk pertanyaan "berapa": Sebutkan angka exact dari data
- Untuk pertanyaan "siapa": Sebutkan nama exact dari data
- Untuk pertanyaan "kapan": Sebutkan tanggal exact dari data
- Untuk list: Gunakan numbered list (1., 2., 3.)
- Untuk detail: Gunakan bullet points atau paragraf terstruktur

CONTOH JAWABAN YANG BENAR:
 SALAH: "SPK ini kemungkinan untuk instalasi jaringan baru" (menebak!)
 BENAR: "Berdasarkan data, jenis SPK adalah 'aktivasi'"

 SALAH: "Teknisi biasanya datang pagi hari" (asumsi!)
 BENAR: "Data menunjukkan teknisi datang pada 11/Nov/2023 pukul 17:13"

 SALAH: "Terdapat sekitar 5-10 SPK" (tidak exact!)
 BENAR: "Ditemukan 7 SPK dalam database"

RESPONS ANDA (berdasarkan DATA di atas saja):"""

    return prompt


def build_sql_answer_prompt(query: str, sql_result: list, context: dict = None) -> str:
    """
    Build prompt to format SQL result into natural language
    STRICT: Only use data from SQL result
    """
    
    if not sql_result:
        return f"""PERTANYAAN: "{query}"
HASIL SQL: KOSONG (0 data)

TUGAS: Jawab bahwa tidak ada data yang ditemukan.

ATURAN:
1.  JANGAN buat data sendiri
2.  Katakan dengan jelas "Tidak ditemukan data"
3.  Sarankan untuk cek kriteria pencarian

RESPONS:"""
    
    # Format SQL result as readable context
    context_str = "=== HASIL QUERY DATABASE ===\n"
    context_str += f"Jumlah data ditemukan: {len(sql_result)}\n\n"
    
    for i, row in enumerate(sql_result[:10], 1):  # Max 10 rows to show
        context_str += f"--- Data #{i} ---\n"
        for key, value in row.items():
            if value is not None:
                context_str += f"{key}: {value}\n"
        context_str += "\n"
    
    if len(sql_result) > 10:
        context_str += f"... dan {len(sql_result) - 10} data lainnya\n"
    
    prompt = f"""PERTANYAAN USER: "{query}"

{context_str}

TUGAS: Format data di atas menjadi jawaban natural dalam Bahasa Indonesia.

🛡️ ATURAN KETAT:
1.  HANYA gunakan data dari HASIL QUERY di atas
2.  JANGAN tambahkan informasi lain
3.  JANGAN buat nomor/tanggal/nama yang tidak ada di data
4.  Sebutkan jumlah exact jika ada
5.  Format agar mudah dibaca (gunakan bold **X** untuk highlight penting)

FORMAT:
- Jika 1 data: Tampilkan detail lengkap
- Jika banyak data: Buat list numbered
- Selalu sebutkan konteks (misal: "untuk nomor jaringan X")

RESPONS (format natural, HANYA dari data di atas):"""

    return prompt


def build_count_verification_prompt(claimed_count: int, actual_data: list) -> str:
    """
    Verify if LLM's claimed count matches actual data
    """
    
    actual_count = len(actual_data)
    
    prompt = f"""VERIFIKASI JUMLAH DATA:

Claimed count (dari jawaban): {claimed_count}
Actual count (dari database): {actual_count}

Apakah ini match?

ATURAN:
- Jika selisih <= 2: Valid (margin of error untuk aggregation)
- Jika selisih > 2: Invalid (kemungkinan halusinasi)

HASIL VERIFIKASI:"""

    return prompt


# ==========================================
# VALIDATION PROMPTS
# ==========================================

def build_entity_extraction_prompt(answer: str) -> str:
    """
    Extract entities from answer for context tracking
    """
    
    prompt = f"""ANSWER: "{answer}"

TUGAS: Extract entities untuk context tracking.

EXTRACT:
1. no_jaringan (10 digit number)
2. no_spk (format: angka/huruf/dash)
3. nama_pelanggan (uppercase names)
4. nama_vendor
5. nama_teknisi

OUTPUT FORMAT (JSON only):
{{
    "no_jaringan": "...",
    "no_spk": "...",
    "pelanggan": "...",
    "vendor": "...",
    "teknisi": "..."
}}

Jika tidak ditemukan, isi dengan null.

JSON OUTPUT:"""

    return prompt


def build_hallucination_check_prompt(answer: str, source_data: str) -> str:
    """
    Check if answer contains hallucinated information
    """
    
    prompt = f"""ANSWER TO CHECK: "{answer}"

SOURCE DATA:
{source_data}

TUGAS: Cek apakah jawaban mengandung informasi yang TIDAK ADA di source data.

CEK:
1. Nomor-nomor (no_jaringan, no_spk) - apakah ada di source?
2. Nama (pelanggan, vendor, teknisi) - apakah ada di source?
3. Tanggal - apakah ada di source?
4. Jumlah/count - apakah sesuai dengan data?

OUTPUT FORMAT (JSON):
{{
    "is_valid": true/false,
    "hallucinated_items": ["item1", "item2"],
    "severity": "none"/"low"/"high"/"critical"
}}

JSON OUTPUT:"""

    return prompt