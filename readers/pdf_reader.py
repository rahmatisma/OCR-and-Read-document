# pdf_reader.py
"""
PDF Reader dengan ekstraksi teks dan gambar dokumentasi
Updated: Support OCR-based image extraction untuk PDF scan
"""

import fitz
from readers.ocr.processor import process_pdf_with_images, process_page_ocr
from dispatcher import dispatch_parser


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
    ocr_data = []  # Store OCR data with page numbers

    # 🔹 Langkah 1: Ambil teks per halaman
    print("[INFO] Step 1: Ekstraksi teks...")
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()

        if not text:
            print(f"[INFO] Halaman {page_number} kosong → OCR dijalankan...")
            ocr_result = process_page_ocr(page, return_data=True)
            
            if isinstance(ocr_result, dict) and 'text' in ocr_result and 'data' in ocr_result:
                text = ocr_result['text']
                # Store OCR data dengan nomor halaman
                for item in ocr_result['data']:
                    item['page_number'] = page_number  # Tambah page number ke setiap item
                ocr_data.extend(ocr_result['data'])
            elif isinstance(ocr_result, str):
                text = ocr_result
            else:
                text = ""

        all_text += text + "\n"
        per_page_text.append({"halaman": page_number, "text": text})

    doc.close()

    # 🔹 Langkah 2: Deteksi jenis dokumen dan parsing via dispatcher
    print("[INFO] Step 2: Deteksi jenis dokumen dan parsing...")
    parsed_result = dispatch_parser(all_text, per_page_text, ocr_data=ocr_data)
    
    doc_type = parsed_result.get("document_type", "unknown")
    print(f"[INFO] Jenis dokumen: {doc_type}")

    # 🔹 Langkah 3: Ekstraksi gambar dokumentasi berdasarkan doc_type
    print("[INFO] Step 3: Ekstraksi gambar dokumentasi...")
    dokumentasi_images = []
    
    if doc_type != "unknown":
        # 🆕 PASS OCR_DATA ke image extraction
        dokumentasi_images = process_pdf_with_images(
            pdf_path=pdf_path, 
            doc_type=doc_type,
            ocr_data=ocr_data  # ← NEW: Pass OCR data untuk PDF scan
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
            "ocr_data_items": len(ocr_data),
            "has_ocr_data": len(ocr_data) > 0
        }

    # Tambahkan di pdf_reader.py setelah loop OCR
    if ocr_data:
        print("\n[DEBUG] Sample OCR data format:")
        for i, item in enumerate(ocr_data[:3]):  # Print 3 item pertama
            print(f"  Item {i}:")
            print(f"    - text: {item.get('text', 'N/A')}")
            print(f"    - bbox: {item.get('bbox', 'N/A')}")
            print(f"    - bbox type: {type(item.get('bbox', None))}")
            if 'bbox' in item and item['bbox']:
                print(f"    - bbox[0]: {item['bbox'][0]} (type: {type(item['bbox'][0])})")
            print()
    print(f"[INFO] ✓ Proses selesai! Total dokumentasi: {len(dokumentasi_images)}")
    return result