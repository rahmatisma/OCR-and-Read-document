# pdf_reader.py - FIXED VERSION
"""
PDF Reader dengan ekstraksi teks dan gambar dokumentasi
 FIXED: Smart OCR detection - only use OCR when truly needed
 FIXED: Proper text layer detection
"""

import fitz
from readers.ocr.processor import process_pdf_with_images, process_page_ocr
from dispatcher import dispatch_parser


def read_pdf(pdf_path: str, debug: bool = False, output_dir: str = None, force_ocr: bool = False) -> dict:
    """
    Membaca dokumen PDF dengan alur:
    1. Ekstrak teks per halaman (OCR hanya jika text layer kosong/tidak valid)
    2. Deteksi jenis dokumen via dispatcher
    3. Ekstrak gambar dokumentasi sesuai jenis dokumen
    4. Parse dokumen sesuai template
    5. Gabungkan hasil
    
    Args:
        pdf_path: Path ke file PDF
        debug: Mode debug untuk output tambahan
        output_dir: Direktori output untuk gambar
        force_ocr: Force OCR even if text layer exists (untuk testing/debugging)
    """
    print(f"[INFO] Membaca dokumen PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    all_text = ""
    per_page_text = []
    ocr_data = []  # List of lists (per page)

    # 🔹 Langkah 1: Ambil teks per halaman
    print("[INFO] Step 1: Ekstraksi teks...")
    
    for page_number, page in enumerate(doc, start=1):
        text = ""
        page_ocr_data = []
        
        #  FIXED: Smart text layer detection
        if not force_ocr:
            text = page.get_text("text").strip()
            
            # Check if text is actually meaningful (not just whitespace/artifacts)
            text_cleaned = text.replace("\n", "").replace(" ", "").replace("\t", "").strip()
            
            #  FIXED: Only use OCR if text layer is truly empty or too short
            if len(text_cleaned) >= 20:  # Has meaningful text (at least 20 chars)
                print(f"[INFO] Halaman {page_number}: Using text layer ({len(text)} chars)")
            else:
                # Text layer insufficient, use OCR
                print(f"[INFO] Halaman {page_number}: Text layer insufficient → Running OCR...")
                text = ""  # Reset to trigger OCR below
        
        # Use OCR if force_ocr=True or text is empty
        if force_ocr or not text:
            if force_ocr:
                print(f"[INFO] Halaman {page_number}: Force OCR enabled → Running OCR...")
            
            ocr_result = process_page_ocr(page, return_data=True)
            
            if isinstance(ocr_result, dict) and 'text' in ocr_result and 'data' in ocr_result:
                text = ocr_result['text']
                page_ocr_data = ocr_result['data']
                print(f"  ✓ OCR extracted {len(text)} chars, {len(page_ocr_data)} items")
            elif isinstance(ocr_result, str):
                text = ocr_result
                print(f"  ✓ OCR extracted {len(text)} chars (no structured data)")
            else:
                text = ""
                print(f"  ✗ OCR failed")

        all_text += text + "\n"
        per_page_text.append({"halaman": page_number, "text": text})
        ocr_data.append(page_ocr_data)

    doc.close()

    # Debug info
    if debug:
        print(f"\n[DEBUG] Total text extracted: {len(all_text)} characters")
        print(f"[DEBUG] OCR data pages: {len(ocr_data)}")
        print(f"[DEBUG] First 200 chars of text:\n{all_text[:200]}\n")

    # 🔹 Langkah 2: Deteksi jenis dokumen dan parsing via dispatcher
    print("[INFO] Step 2: Deteksi jenis dokumen dan parsing...")
    
    # Only pass OCR data if we actually have data
    has_ocr = any(len(page_data) > 0 for page_data in ocr_data)
    
    if has_ocr:
        print(f"[INFO] Passing OCR data to dispatcher ({sum(len(p) for p in ocr_data)} total items)")
        parsed_result = dispatch_parser(all_text, per_page_text, ocr_data=ocr_data)
    else:
        print(f"[INFO] No OCR data, using text-only parsing")
        parsed_result = dispatch_parser(all_text, per_page_text, ocr_data=None)
    
    doc_type = parsed_result.get("document_type", "unknown")
    print(f"[INFO] Jenis dokumen: {doc_type}")

    # 🔹 Langkah 3: Ekstraksi gambar dokumentasi berdasarkan doc_type
    print("[INFO] Step 3: Ekstraksi gambar dokumentasi...")
    dokumentasi_images = []
    
    if doc_type != "unknown":
        if output_dir:
            print(f"[INFO] Output gambar akan disimpan di: {output_dir}")
            dokumentasi_images = process_pdf_with_images(
                pdf_path=pdf_path, 
                doc_type=doc_type,
                ocr_data=ocr_data if has_ocr else None,
                output_dir=output_dir
            )
        else:
            print(f"[WARNING] output_dir tidak diberikan, menggunakan default 'output/images'")
            dokumentasi_images = process_pdf_with_images(
                pdf_path=pdf_path, 
                doc_type=doc_type,
                ocr_data=ocr_data if has_ocr else None
            )
    else:
        print("[WARNING] Skip ekstraksi gambar karena doc_type unknown")

    # 🔹 Langkah 4: Gabungkan hasil
    result = {
        "dokumentasi": dokumentasi_images,
        "parsed": parsed_result,
        "all_text": all_text
    }

    if debug:
        result["_debug"] = {
            "raw_all_text": all_text,
            "per_page_text": per_page_text,
            "doc_type": doc_type,
            "total_pages": len(per_page_text),
            "total_images": len(dokumentasi_images),
            "ocr_data_pages": len(ocr_data),
            "ocr_data_items": sum(len(p) for p in ocr_data),
            "has_ocr_data": has_ocr
        }
    
    print(f"[INFO] ✓ Proses selesai! Total dokumentasi: {len(dokumentasi_images)}")
    return result