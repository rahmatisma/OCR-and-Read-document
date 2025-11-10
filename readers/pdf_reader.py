# pdf_reader.py
"""
PDF Reader dengan ekstraksi teks dan gambar dokumentasi
"""

import fitz
from readers.ocr.processor import process_pdf_with_images, process_page_ocr
from dispatcher import dispatch_parser


# pdf_reader.py (UPDATE bagian dispatcher)

def read_pdf(pdf_path: str, debug: bool = False) -> dict:
    """
    Membaca dokumen PDF dengan alur:
    1. Ekstrak teks per halaman (OCR jika perlu) + SIMPAN OCR DATA
    2. Deteksi jenis dokumen via dispatcher
    3. Ekstrak gambar dokumentasi sesuai jenis dokumen
    4. Parse dokumen sesuai template
    5. Gabungkan hasil
    """
    print(f"[INFO] Membaca dokumen PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    all_text = ""
    per_page_text = []
    ocr_data = []  # ← TAMBAHKAN INI

    # 🔹 Langkah 1: Ambil teks per halaman
    print("[INFO] Step 1: Ekstraksi teks...")
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()

        if not text:
            print(f"[INFO] Halaman {page_number} kosong → OCR dijalankan...")
            # ========== UPDATE INI ==========
            # SEBELUMNYA:
            # text = process_page_ocr(page)  # ← Hanya dapat text
            
            # SEKARANG:
            ocr_result = process_page_ocr(page, return_data=True)  # ← Dapat full OCR data
            
            if isinstance(ocr_result, dict) and 'text' in ocr_result and 'data' in ocr_result:
                # OCR function mengembalikan dict dengan text dan data
                text = ocr_result['text']
                ocr_data.extend(ocr_result['data'])  # ← SIMPAN OCR DATA
            elif isinstance(ocr_result, str):
                # Fallback jika OCR function hanya return text
                text = ocr_result
            else:
                text = ""
            # ================================

        all_text += text + "\n"
        per_page_text.append({"halaman": page_number, "text": text})

    doc.close()

    # 🔹 Langkah 2: Deteksi jenis dokumen dan parsing via dispatcher
    print("[INFO] Step 2: Deteksi jenis dokumen dan parsing...")
    # ========== PASS OCR DATA KE DISPATCHER ==========
    parsed_result = dispatch_parser(all_text, per_page_text, ocr_data=ocr_data)  # ← TAMBAHKAN ocr_data
    # =================================================
    
    # Ambil doc_type dari hasil dispatcher
    doc_type = parsed_result.get("document_type", "unknown")
    print(f"[INFO] Jenis dokumen: {doc_type}")

    # 🔹 Langkah 3: Ekstrak gambar dokumentasi berdasarkan doc_type
    print("[INFO] Step 3: Ekstraksi gambar dokumentasi...")
    dokumentasi_images = []
    
    if doc_type != "unknown":
        dokumentasi_images = process_pdf_with_images(
            pdf_path=pdf_path, 
            doc_type=doc_type
        )
    else:
        print("[WARNING] Skip ekstraksi gambar karena doc_type unknown")

    # 🔹 Langkah 4: Gabungkan hasil
    result = {
        "dokumentasi": dokumentasi_images,
        "parsed": parsed_result
    }

    if debug:
        result["_debug"] = {
            "raw_all_text": all_text,
            "per_page_text": per_page_text,
            "doc_type": doc_type,
            "total_pages": len(per_page_text),
            "total_images": len(dokumentasi_images),
            "ocr_data_items": len(ocr_data)  # ← TAMBAHKAN INI untuk debug
        }

    print(f"[INFO] ✓ Proses selesai! Total dokumentasi: {len(dokumentasi_images)}")
    return result