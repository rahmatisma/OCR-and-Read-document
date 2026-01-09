"""
database_schema.py

COMPLETE Database Schema - Based on DBML
SPK Management System PT. Lintasarta
"""

# ============================================
# CORE TABLES (Yang akan di-expose ke LLM)
# ============================================

CORE_TABLES = {
    "jaringan": {
        "description": "Data pelanggan dan jaringan telekomunikasi",
        "columns": [
            {"name": "no_jaringan", "type": "VARCHAR(100)", "key": "PRIMARY KEY", "description": "Nomor jaringan unik (10 digit), contoh: '2021242440'"},
            {"name": "nama_pelanggan", "type": "VARCHAR(255)", "description": "Nama pelanggan, contoh: 'BANK NEGARA INDONESIA 1946 (PERSERO)'"},
            {"name": "lokasi_pelanggan", "type": "TEXT", "description": "Alamat lokasi pelanggan"},
            {"name": "jasa", "type": "VARCHAR(100)", "description": "Jenis layanan: 'LA_IPVPN', 'LA_METRO_ETHERNET', dll"},
            {"name": "media_akses", "type": "VARCHAR(100)", "description": "Media akses jaringan"},
            {"name": "kecepatan", "type": "VARCHAR(255)", "description": "Kecepatan internet, contoh: 'Downstream / Upstream 1000 Mbps'"},
            {"name": "pop", "type": "TEXT", "description": "Point of Presence, contoh: 'JKTRMCSR01'"},
            {"name": "tgl_rfs_la", "type": "DATE", "description": "Tanggal Ready for Service (Lintasarta)"},
            {"name": "tgl_rfs_plg", "type": "DATE", "description": "Tanggal Ready for Service (Pelanggan)"},
            {"name": "is_deleted", "type": "BOOLEAN", "description": "Soft delete flag (0=active, 1=deleted)"},
        ],
        "indexes": ["no_jaringan", "nama_pelanggan", "jasa"],
        "important_notes": [
            "⚠️ WAJIB: Selalu tambahkan 'WHERE is_deleted = 0' atau 'WHERE is_deleted = false'",
            "no_jaringan adalah identifier utama (10 digit)",
            "Gunakan LIKE '%keyword%' untuk search nama_pelanggan (case-insensitive)",
        ]
    },
    
    "spk": {
        "description": "Surat Perintah Kerja (SPK) - dokumen pekerjaan",
        "columns": [
            {"name": "id_spk", "type": "BIGINT", "key": "PRIMARY KEY", "description": "ID unik SPK (auto-increment)"},
            {"name": "no_spk", "type": "VARCHAR(100)", "key": "UNIQUE", "description": "Nomor SPK, format: '065848/WO-LA/2021'"},
            {"name": "no_jaringan", "type": "VARCHAR(100)", "key": "FOREIGN KEY", "description": "Nomor jaringan terkait (10 digit)"},
            {"name": "document_type", "type": "ENUM", "values": ["spk", "form_checklist_wireline", "form_checklist_wireless"], "description": "Tipe dokumen"},
            {"name": "jenis_spk", "type": "ENUM", "values": ["aktivasi", "dismantle", "instalasi", "survey", "maintenance"], "description": "Jenis pekerjaan SPK"},
            {"name": "tanggal_spk", "type": "DATE", "description": "Tanggal pembuatan SPK"},
            {"name": "no_mr", "type": "VARCHAR(100)", "description": "Nomor MR (opsional)"},
            {"name": "no_fps", "type": "VARCHAR(100)", "description": "Nomor FPS (opsional)"},
            {"name": "is_deleted", "type": "BOOLEAN", "description": "Soft delete flag"},
        ],
        "indexes": ["no_spk", "no_jaringan", "jenis_spk", "tanggal_spk"],
        "important_notes": [
            "⚠️ WAJIB: Selalu tambahkan 'WHERE is_deleted = 0'",
            "⚠️ Gunakan JOIN dengan jaringan untuk mendapatkan data pelanggan",
            "jenis_spk HANYA 5 nilai: 'aktivasi', 'dismantle', 'instalasi', 'survey', 'maintenance'",
            "Format no_spk: 6digit/WO-LA/4digit tahun (contoh: '065848/WO-LA/2021')",
        ]
    },
    
    "spk_execution_info": {
        "description": "Informasi eksekusi SPK (teknisi, vendor, PIC pelanggan)",
        "columns": [
            {"name": "id_execution", "type": "BIGINT", "key": "PRIMARY KEY"},
            {"name": "id_spk", "type": "BIGINT", "key": "FOREIGN KEY", "references": "spk.id_spk"},
            {"name": "latitude", "type": "DECIMAL(9,6)", "description": "Koordinat latitude lokasi"},
            {"name": "longitude", "type": "DECIMAL(10,6)", "description": "Koordinat longitude lokasi"},
            {"name": "pic_pelanggan", "type": "VARCHAR(255)", "description": "Person in Charge dari pelanggan"},
            {"name": "kontak_pic_pelanggan", "type": "VARCHAR(20)", "description": "Nomor kontak PIC"},
            {"name": "teknisi", "type": "VARCHAR(255)", "description": "Nama teknisi yang mengerjakan"},
            {"name": "nama_vendor", "type": "VARCHAR(255)", "description": "Nama vendor pelaksana"},
        ],
        "indexes": ["id_spk"],
        "important_notes": [
            "⚠️ Relasi ONE-to-ONE dengan spk (1 SPK = 1 execution info)",
            "⚠️ Gunakan LEFT JOIN karena tidak semua SPK punya execution info",
            "Contoh JOIN: LEFT JOIN spk_execution_info sei ON s.id_spk = sei.id_spk",
        ]
    },
    
    "spk_pelaksanaan": {
        "description": "Waktu pelaksanaan SPK (permintaan, datang, selesai)",
        "columns": [
            {"name": "id_pelaksanaan", "type": "BIGINT", "key": "PRIMARY KEY"},
            {"name": "id_spk", "type": "BIGINT", "key": "FOREIGN KEY", "references": "spk.id_spk"},
            {"name": "permintaan_pelanggan", "type": "TIMESTAMP", "description": "Waktu permintaan dari pelanggan"},
            {"name": "datang", "type": "TIMESTAMP", "description": "Waktu teknisi datang"},
            {"name": "selesai", "type": "TIMESTAMP", "description": "Waktu pekerjaan selesai"},
        ],
        "indexes": ["id_spk"],
        "important_notes": [
            "Gunakan untuk query tentang 'kapan', 'waktu', 'tanggal pelaksanaan'",
            "LEFT JOIN karena tidak semua SPK punya data pelaksanaan",
        ]
    },
    
    "dokumentasi_foto": {
        "description": "Dokumentasi foto dari SPK (survey, instalasi, dll)",
        "columns": [
            {"name": "id_dokumentasi", "type": "BIGINT", "key": "PRIMARY KEY"},
            {"name": "id_spk", "type": "BIGINT", "key": "FOREIGN KEY"},
            {"name": "kategori_foto", "type": "ENUM", "values": [
                "hasil_survey", "hasil_instalasi", "hasil_aktivasi", 
                "hasil_dismantle", "foto_penempatan_perangkat", "foto_jalur_kabel",
                "foto_splitter", "foto_hh_eksisting", "foto_hh_baru", "foto_lain_lain"
            ]},
            {"name": "path_foto", "type": "VARCHAR(1000)", "description": "Path file foto"},
            {"name": "keterangan", "type": "TEXT", "description": "Keterangan foto"},
            {"name": "urutan", "type": "INT", "description": "Urutan foto"},
        ],
        "indexes": ["id_spk", "kategori_foto"],
        "important_notes": [
            "Gunakan untuk query 'berapa foto', 'foto apa saja', 'dokumentasi'",
            "Bisa banyak foto untuk 1 SPK (ONE-to-MANY)",
        ]
    }
}

# ============================================
# RELATIONSHIPS
# ============================================

RELATIONSHIPS = [
    {
        "from": "spk.no_jaringan",
        "to": "jaringan.no_jaringan",
        "type": "MANY-to-ONE",
        "description": "Satu jaringan bisa punya banyak SPK",
        "join_example": "JOIN jaringan j ON s.no_jaringan = j.no_jaringan"
    },
    {
        "from": "spk_execution_info.id_spk",
        "to": "spk.id_spk",
        "type": "ONE-to-ONE",
        "description": "Satu SPK punya satu execution info (atau null)",
        "join_example": "LEFT JOIN spk_execution_info sei ON s.id_spk = sei.id_spk"
    },
    {
        "from": "spk_pelaksanaan.id_spk",
        "to": "spk.id_spk",
        "type": "ONE-to-ONE",
        "description": "Satu SPK punya satu data pelaksanaan (atau null)",
        "join_example": "LEFT JOIN spk_pelaksanaan sp ON s.id_spk = sp.id_spk"
    },
    {
        "from": "dokumentasi_foto.id_spk",
        "to": "spk.id_spk",
        "type": "MANY-to-ONE",
        "description": "Satu SPK bisa punya banyak foto",
        "join_example": "LEFT JOIN dokumentasi_foto df ON s.id_spk = df.id_spk"
    }
]

# ============================================
# COMMON QUERY PATTERNS (Real World Examples)
# ============================================

QUERY_EXAMPLES = {
    "count_spk_by_nojar": {
        "description": "Hitung jumlah SPK untuk nomor jaringan tertentu",
        "query": """
SELECT COUNT(*) as jumlah_spk
FROM spk
WHERE no_jaringan = '2021242440'
AND is_deleted = 0
        """
    },
    
    "list_spk_by_nojar": {
        "description": "Tampilkan list SPK untuk nomor jaringan",
        "query": """
SELECT s.no_spk, s.jenis_spk, s.tanggal_spk, s.no_jaringan
FROM spk s
WHERE s.no_jaringan = '2021242440'
AND s.is_deleted = 0
ORDER BY s.tanggal_spk DESC
        """
    },
    
    "get_pelanggan_info": {
        "description": "Ambil informasi pelanggan dari nomor jaringan",
        "query": """
SELECT j.nama_pelanggan, j.lokasi_pelanggan, j.pop, j.jasa, j.kecepatan
FROM jaringan j
WHERE j.no_jaringan = '2021242440'
AND j.is_deleted = 0
        """
    },
    
    "get_spk_with_teknisi": {
        "description": "Ambil SPK beserta teknisi dan vendor",
        "query": """
SELECT 
    s.no_spk, 
    s.jenis_spk, 
    s.tanggal_spk,
    j.nama_pelanggan,
    sei.teknisi, 
    sei.nama_vendor
FROM spk s
JOIN jaringan j ON s.no_jaringan = j.no_jaringan
LEFT JOIN spk_execution_info sei ON s.id_spk = sei.id_spk
WHERE s.no_jaringan = '2021242440'
AND s.is_deleted = 0
        """
    },
    
    "filter_spk_by_jenis": {
        "description": "Filter SPK berdasarkan jenis (aktivasi, maintenance, dll)",
        "query": """
SELECT s.no_spk, s.jenis_spk, s.tanggal_spk, sei.teknisi
FROM spk s
LEFT JOIN spk_execution_info sei ON s.id_spk = sei.id_spk
WHERE s.no_jaringan = '2021242440'
AND s.jenis_spk = 'aktivasi'
AND s.is_deleted = 0
        """
    },
    
    "count_foto_by_spk": {
        "description": "Hitung jumlah foto dokumentasi untuk SPK",
        "query": """
SELECT COUNT(*) as jumlah_foto
FROM dokumentasi_foto
WHERE id_spk = (
    SELECT id_spk FROM spk WHERE no_spk = '065848/WO-LA/2021' AND is_deleted = 0
)
        """
    },
    
    "search_pelanggan_by_name": {
        "description": "Cari pelanggan berdasarkan nama (partial match)",
        "query": """
SELECT j.no_jaringan, j.nama_pelanggan, j.lokasi_pelanggan, j.pop
FROM jaringan j
WHERE j.nama_pelanggan LIKE '%BANK%'
AND j.is_deleted = 0
LIMIT 10
        """
    }
}

# ============================================
# SQL RULES & BEST PRACTICES
# ============================================

SQL_RULES = [
    "✅ SELALU tambahkan 'WHERE is_deleted = 0' atau 'WHERE is_deleted = false' untuk tabel spk dan jaringan",
    "✅ Gunakan LEFT JOIN untuk spk_execution_info karena tidak semua SPK punya data eksekusi",
    "✅ Gunakan alias tabel yang jelas: spk → s, jaringan → j, spk_execution_info → sei",
    "✅ Untuk COUNT, gunakan COUNT(*) atau COUNT(DISTINCT column_name)",
    "✅ Untuk search nama pelanggan, gunakan LIKE '%keyword%' (case-insensitive)",
    "✅ Selalu ORDER BY tanggal_spk DESC untuk menampilkan data terbaru dulu",
    "✅ Gunakan LIMIT jika query bisa return banyak data (default: LIMIT 100)",
    "❌ JANGAN gunakan SELECT * di production (pilih column spesifik saja)",
    "❌ JANGAN lupa JOIN jaringan jika butuh data pelanggan",
]

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_schema_as_text() -> str:
    """Generate schema text untuk LLM prompt"""
    schema_text = "=== DATABASE SCHEMA ===\n\n"
    
    for table_name, table_info in CORE_TABLES.items():
        schema_text += f"📊 TABLE: {table_name}\n"
        schema_text += f"   {table_info['description']}\n\n"
        schema_text += "   Columns:\n"
        
        for col in table_info['columns']:
            key_info = f" [{col['key']}]" if 'key' in col else ""
            values_info = f"\n      Values: {', '.join(col['values'])}" if 'values' in col else ""
            schema_text += f"   • {col['name']} ({col['type']}){key_info}{values_info}\n"
            description = col.get('description', 'No description')
            schema_text += f"     → {description}\n"
        
        if table_info.get('important_notes'):
            schema_text += "\n   ⚠️  IMPORTANT NOTES:\n"
            for note in table_info['important_notes']:
                schema_text += f"      {note}\n"
        
        schema_text += "\n" + "-" * 80 + "\n\n"
    
    return schema_text


def get_relationships_text() -> str:
    """Generate relationships text untuk LLM"""
    rel_text = "=== TABLE RELATIONSHIPS ===\n\n"
    
    for rel in RELATIONSHIPS:
        rel_text += f"🔗 {rel['from']} → {rel['to']} ({rel['type']})\n"
        rel_text += f"   {rel['description']}\n"
        rel_text += f"   Example: {rel['join_example']}\n\n"
    
    return rel_text


def get_query_examples_text() -> str:
    """Generate query examples untuk LLM"""
    examples_text = "=== EXAMPLE QUERIES ===\n\n"
    
    for name, example in QUERY_EXAMPLES.items():
        examples_text += f"📝 {name}:\n"
        examples_text += f"   {example['description']}\n"
        examples_text += f"{example['query'].strip()}\n\n"
    
    return examples_text


def get_sql_rules_text() -> str:
    """Generate SQL rules untuk LLM"""
    rules_text = "=== SQL RULES & BEST PRACTICES ===\n\n"
    
    for rule in SQL_RULES:
        rules_text += f"{rule}\n"
    
    return rules_text


def get_complete_schema_for_llm() -> str:
    """
    Generate COMPLETE schema text siap pakai untuk LLM prompt
    """
    return (
        get_schema_as_text() + 
        get_relationships_text() + 
        get_query_examples_text() + 
        get_sql_rules_text()
    )


def get_allowed_tables() -> list:
    """Return list allowed table names"""
    return list(CORE_TABLES.keys())


def validate_table_name(table_name: str) -> bool:
    """Check if table name is allowed"""
    return table_name.lower() in [t.lower() for t in CORE_TABLES.keys()]


if __name__ == "__main__":
    # Test: Print complete schema
    print(get_complete_schema_for_llm())
    print("\n" + "=" * 80)
    print("📋 Allowed Tables:", get_allowed_tables())