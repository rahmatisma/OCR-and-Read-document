"""
Ekstraksi gambar dokumentasi dengan support untuk PDF scan (OCR-based)
- Support PDF native (text layer) 
- Support PDF scan (OCR coordinates)
"""

import fitz  # PyMuPDF
import os
import re
from .label_config import LabelConfig


def normalize_name(label: str) -> str:
    """Ubah label menjadi nama file yang aman."""
    name = label.lower().replace(" ", "_").replace("/", "_")
    return name


def get_nearby_text(page, rect, margin=200):
    """Ambil teks di sekitar rectangle."""
    clip_box = fitz.Rect(
        max(0, rect.x0 - 5),
        max(0, rect.y0 - 5),
        min(page.rect.width, rect.x1 + margin),
        rect.y1 + 5
    )
    text = page.get_textbox(clip_box).strip()
    return re.sub(r'\s+', ' ', text)


def is_valid_header(page, rect, label, min_font_size=10, ocr_mode=False):
    """
    Validasi apakah rect ini adalah HEADER section.
    
    Args:
        page: PyMuPDF page object
        rect: Rectangle koordinat
        label: Label text yang dicari
        min_font_size: Minimum font size untuk header
        ocr_mode: Jika True, skip font size check (karena OCR tidak punya font info)
    """
    
    # 1️⃣ CEK FONT SIZE - Skip untuk OCR mode
    if not ocr_mode:
        text_blocks = page.get_text("dict")["blocks"]
        label_font_size = None
        
        for block in text_blocks:
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_bbox = fitz.Rect(span["bbox"])
                        if span_bbox.intersects(rect):
                            label_font_size = span.get("size", 0)
                            break
                    if label_font_size:
                        break
            if label_font_size:
                break
        
        if label_font_size is None:
            print(f"   [SKIP] '{label}' - font size tidak terdeteksi")
            return False
        
        if label_font_size < min_font_size:
            print(f"   [SKIP] '{label}' - font terlalu kecil: {label_font_size:.1f}pt")
            return False
    
    # 2️⃣ CEK KONTEKS KIRI
    left_margin = 100
    left_check_box = fitz.Rect(
        max(0, rect.x0 - left_margin),
        rect.y0 - 3,
        rect.x0 - 5,
        rect.y1 + 3
    )
    left_text = page.get_textbox(left_check_box).strip()
    
    if left_text and len(left_text) > 3:
        print(f"   [SKIP] '{label}' - ada awalan: '{left_text}'")
        return False
    
    # 3️⃣ CEK POSISI
    relative_y = rect.y0 / page.rect.height
    if relative_y > 0.85:
        print(f"   [SKIP] '{label}' - posisi terlalu bawah: {relative_y:.1%}")
        return False
    
    if ocr_mode:
        print(f"   [✓] '{label}' header valid (OCR mode, pos: {relative_y:.1%})")
    else:
        label_font_size = label_font_size if label_font_size else 0
        print(f"   [✓] '{label}' header valid (pos: {relative_y:.1%}, font: {label_font_size:.1f}pt)")
    
    return True


def normalize_bbox_to_rect(bbox):
    """
    🆕 Convert berbagai format bbox menjadi fitz.Rect.
    
    PaddleOCR bisa return:
    - Format 1: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]  # Polygon 4 corners
    - Format 2: [x1, y1, x2, y2]                       # Rectangle
    
    Returns:
        fitz.Rect(x_min, y_min, x_max, y_max)
    """
    if not bbox:
        return None
    
    try:
        # Format 1: Nested list (polygon) [[x1,y1], [x2,y2], ...]
        if isinstance(bbox[0], (list, tuple)):
            # Flatten polygon ke list of coordinates
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            
            # Get bounding box dari polygon
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            
            return fitz.Rect(x_min, y_min, x_max, y_max)
        
        # Format 2: Flat list [x1, y1, x2, y2]
        elif len(bbox) == 4 and all(isinstance(x, (int, float)) for x in bbox):
            return fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        
        # Format 3: Flat list dengan lebih dari 4 nilai (ambil min/max)
        elif len(bbox) >= 4:
            # Assume alternating x, y coordinates
            xs = [bbox[i] for i in range(0, len(bbox), 2)]
            ys = [bbox[i] for i in range(1, len(bbox), 2)]
            
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            
            return fitz.Rect(x_min, y_min, x_max, y_max)
        
        else:
            print(f"   [ERROR] Unrecognized bbox format: {bbox}")
            return None
            
    except Exception as e:
        print(f"   [ERROR] Failed to parse bbox {bbox}: {e}")
        return None


def find_label_from_ocr(ocr_data, page_number, label, exclude_keywords=None):
    """
    🆕 Cari label menggunakan OCR data (untuk PDF scan).
    
    Args:
        ocr_data: List of OCR items dengan format:
                    [{'text': str, 'bbox': [...], 'page_number': int, ...}, ...]
        page_number: Nomor halaman yang dicari (1-indexed)
        label: Label text yang dicari
        exclude_keywords: Keywords untuk exclude
    
    Returns:
        fitz.Rect atau None
    """
    if not ocr_data:
        return None
    
    if exclude_keywords is None:
        exclude_keywords = []
    
    # Filter OCR data untuk halaman ini
    page_ocr = [item for item in ocr_data if item.get('page_number') == page_number]
    
    if not page_ocr:
        print(f"   [INFO] Tidak ada OCR data untuk halaman {page_number}")
        return None
    
    print(f"   [DEBUG] Mencari '{label}' di {len(page_ocr)} OCR items (halaman {page_number})")
    
    # Debug: Print sample OCR items
    if page_ocr:
        print(f"   [DEBUG] Sample OCR items (first 3):")
        for i, item in enumerate(page_ocr[:3]):
            text_preview = item.get('text', '')[:30]
            bbox_preview = str(item.get('bbox', 'N/A'))[:50]
            print(f"     [{i}] text='{text_preview}...', bbox={bbox_preview}...")
    
    # Cari label dengan fuzzy matching (case insensitive, ignore whitespace)
    label_normalized = label.lower().replace(" ", "").replace(":", "")
    
    for idx, item in enumerate(page_ocr):
        text = item.get('text', '')
        text_normalized = text.lower().replace(" ", "").replace(":", "")
        
        # Check apakah text mengandung label (fuzzy match)
        if label_normalized in text_normalized:
            bbox = item.get('bbox')
            if not bbox:
                print(f"   [SKIP] Item {idx}: '{text}' - bbox kosong")
                continue
            
            # 🔧 Convert bbox ke fitz.Rect (support multiple formats)
            rect = normalize_bbox_to_rect(bbox)
            if not rect:
                print(f"   [SKIP] Item {idx}: '{text}' - bbox tidak valid: {bbox}")
                continue
            
            # Check exclude keywords (cek context di sekitar)
            context_text = text.lower()
            
            # Cari teks lain yang berdekatan untuk context
            for other in page_ocr:
                other_bbox = other.get('bbox')
                if not other_bbox:
                    continue
                
                other_rect = normalize_bbox_to_rect(other_bbox)
                if not other_rect:
                    continue
                
                # Check kalau berdekatan (dalam radius 200px pada Y axis)
                if abs(other_rect.y0 - rect.y0) < 200:
                    context_text += " " + other.get('text', '').lower()
            
            # Skip kalau ada exclude keyword
            if any(kw.lower() in context_text for kw in exclude_keywords):
                print(f"   [SKIP] '{text}' - mengandung exclude keyword")
                continue
            
            print(f"   [✓] Found '{text}' via OCR at rect ({rect.x0:.1f}, {rect.y0:.1f}, {rect.x1:.1f}, {rect.y1:.1f})")
            return rect
    
    print(f"   [INFO] Label '{label}' tidak ditemukan di halaman {page_number}")
    return None


def find_exact_label(page, label, exclude_keywords=None, ocr_data=None, page_number=None):
    """
    Cari label dengan exact matching - support native PDF dan OCR.
    
    Args:
        page: PyMuPDF page object
        label: Label text yang dicari
        exclude_keywords: Keywords untuk exclude
        ocr_data: OCR data (untuk PDF scan) - NEW!
        page_number: Nomor halaman (untuk OCR lookup) - NEW!
    """
    if exclude_keywords is None:
        exclude_keywords = []
    
    # 🆕 PRIORITAS 1: Coba cari dengan OCR data (untuk PDF scan)
    if ocr_data and page_number:
        print(f"   [INFO] Mode: OCR-based search (PDF scan)")
        ocr_rect = find_label_from_ocr(ocr_data, page_number, label, exclude_keywords)
        
        if ocr_rect:
            # Validasi header dengan OCR mode
            if is_valid_header(page, ocr_rect, label, ocr_mode=True):
                return ocr_rect
    
    # 🔄 FALLBACK: Coba text layer (untuk PDF native)
    print(f"   [INFO] Mode: Text layer search (PDF native)")
    text_instances = page.search_for(label, quads=False)
    
    if not text_instances:
        return None

    for rect in text_instances:
        # Cek exclude keywords
        nearby = get_nearby_text(page, rect, margin=250).lower()
        if any(keyword.lower() in nearby for keyword in exclude_keywords):
            continue
        
        # Validasi header (native mode)
        if not is_valid_header(page, rect, label, ocr_mode=False):
            continue
        
        return rect
    
    return None


def get_exclude_keywords_for_label(label):
    """Kata yang harus dihindari agar tidak salah tangkap."""
    exclude_map = {
        "dokumentasi foto": ["provisioning"],
        "hasil aktivasi": ["capture", "dokumentasi foto"],
    }
    return exclude_map.get(label.lower(), [])


def crop_from_label(page, label_rect, top_margin=15):
    """
    Crop dari ATAS label (bukan bawah) sampai akhir halaman.
    
    Args:
        page: PyMuPDF page object
        label_rect: Rectangle koordinat label
        top_margin: Jarak ke atas dari label (default 50px untuk include area di atas label)
    """
    # Mulai crop dari ATAS label (y0) dikurangi margin, bukan dari bawah (y1)
    crop_box = fitz.Rect(
        0,
        max(0, label_rect.y0 - top_margin),  # ← Mulai dari ATAS label - margin
        page.rect.width,
        page.rect.height
    )
    return page.get_pixmap(clip=crop_box)


def crop_full_page(page):
    """Crop seluruh halaman."""
    return page.get_pixmap()


def generate_section_keywords(target_labels):
    """Generate section keywords untuk deteksi section baru."""
    common_keywords = [
        "DATA PENEMPATAN PERANGKAT DI LOKASI PELANGGAN",
        "DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM KAWASAN",
        "DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM GEDUNG",
        "DATA SPLITTER",
        "DATA HH EKSISTING YANG DIPAKAI",
        "DATA HH BARU",
        "DATA TIANG EKSISTING",
        "DATA TIANG BARU",
        "DATA KAWASAN UMUM",
        "DATA JALUR KABEL",
        "TIME FRAME PEKERJAAN",
        "INFO LAIN LAIN",
        "BOQ FO",
        "BERITA ACARA",
    ]
    
    all_keywords = list(set([label.upper() for label in target_labels] + common_keywords))
    return all_keywords


def extract_and_classify_images(pdf_path, doc_type, output_dir="output/images", ocr_data=None):
    """
    🆕 Ekstraksi gambar dengan support PDF scan (OCR) dan native.
    
    Args:
        pdf_path: Path ke file PDF
        doc_type: Jenis dokumen
        output_dir: Direktori output
        ocr_data: OCR data dengan bbox coordinates (NEW!)
    """
    all_labels = LabelConfig.get_labels(doc_type)
    if not all_labels:
        print(f"[ERROR] Tidak ada label untuk doc_type: {doc_type}")
        return []

    target_labels = all_labels
    
    if not target_labels:
        print(f"[WARNING] Tidak ada label ditemukan untuk {doc_type}")
        return []
    
    print(f"[INFO] Total label yang akan diproses: {len(target_labels)}")
    print(f"[INFO] Label: {target_labels}")
    print(f"[INFO] OCR mode: {'ENABLED (PDF scan)' if ocr_data else 'DISABLED (PDF native)'}")

    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    print(f"[INFO] Membuka {pdf_path} dengan {len(doc)} halaman...")

    results = []
    processed_label_per_page = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_number = page_num + 1  # 1-indexed

        # Cek setiap label di halaman ini
        for label in target_labels:
            # Skip kalau label sudah diproses
            if processed_label_per_page.get(page_num) == label:
                continue
            
            exclude_keywords = get_exclude_keywords_for_label(label)
            
            # 🆕 Pass OCR data dan page number
            label_rect = find_exact_label(
                page, 
                label, 
                exclude_keywords,
                ocr_data=ocr_data,
                page_number=page_number
            )

            if label_rect:
                print(f"[INFO] Menemukan '{label}' di halaman {page_number}")

                # Crop dari bawah label
                pix = crop_from_label(page, label_rect)
                if pix:
                    filename = f"{normalize_name(label)}_hal{page_number}.jpg"
                    out_path = os.path.join(output_dir, filename)
                    pix.save(out_path)
                    print(f"[OK] {label} → {out_path}")

                    results.append({"jenis": label, "patch_foto": out_path})
                    processed_label_per_page[page_num] = label

                # === CONTINUATION LOGIC (sama seperti sebelumnya) ===
                next_page_num = page_num + 1
                while next_page_num < len(doc):
                    next_page = doc[next_page_num]
                    next_page_number = next_page_num + 1
                    text_upper = next_page.get_text("text").upper()

                    ignored_headers = ["SURVEY REPORT", "JARINGAN :", "LINTASARTA", "PORT KOSONG", "INSTALASI REPORT"]
                    found_new_label = False
                    section_in_top_area = False
                    next_section_y = None

                    # Check section non-foto
                    non_foto_keywords = [
                        "BOQ ETHERNET", "BOQ FO", "BOQ", "LIST ITEM", "BERITA ACARA",
                        "DOKUMENTASI FOTO PROVISIONING", "TIME FRAME PEKERJAAN"
                    ]
                    
                    for keyword in non_foto_keywords:
                        if keyword in text_upper:
                            rects = next_page.search_for(keyword)
                            if rects:
                                avg_y = sum([r.y0 for r in rects]) / len(rects)
                                if avg_y < next_page.rect.height * 0.3:
                                    print(f"[INFO] Halaman {next_page_number}: Section non-foto '{keyword}' → stop")
                                    found_new_label = True
                                    section_in_top_area = True
                                    break

                    if found_new_label and section_in_top_area:
                        break

                    # Check halaman dengan konten sedikit
                    text_content = next_page.get_text("text").strip()
                    word_count = len(text_content.split())
                    
                    if word_count < 20:
                        has_new_label = False
                        for check_label in target_labels:
                            if check_label.lower() != label.lower():
                                # 🆕 Gunakan OCR-aware search
                                check_rect = find_exact_label(
                                    next_page, 
                                    check_label, 
                                    [],
                                    ocr_data=ocr_data,
                                    page_number=next_page_number
                                )
                                if check_rect:
                                    has_new_label = True
                                    print(f"[INFO] Halaman {next_page_number}: Label baru '{check_label}' → stop")
                                    break
                        
                        if has_new_label:
                            break
                        
                        print(f"[INFO] Halaman {next_page_number}: Konten sedikit, ambil full page")
                        cont_pix = crop_full_page(next_page)
                        
                        cont_filename = f"{normalize_name(label)}_hal{next_page_number}.jpg"
                        cont_out_path = os.path.join(output_dir, cont_filename)
                        cont_pix.save(cont_out_path)
                        print(f"[OK] Continuation '{label}' → {cont_out_path}")
                        
                        results.append({"jenis": label, "patch_foto": cont_out_path})
                        processed_label_per_page[next_page_num] = label
                        
                        next_page_num += 1
                        continue

                    # Check label foto baru di halaman next
                    for next_label in target_labels:
                        if next_label.lower() != label.lower():
                            # 🆕 OCR-aware search
                            next_rect = find_exact_label(
                                next_page,
                                next_label,
                                [],
                                ocr_data=ocr_data,
                                page_number=next_page_number
                            )
                            if next_rect:
                                found_new_label = True
                                section_in_top_area = True
                                print(f"[INFO] Halaman {next_page_number}: Label '{next_label}' → stop")
                                break

                    # Generate section keywords dan cek posisi
                    section_keywords = generate_section_keywords(all_labels)

                    if not found_new_label:
                        for keyword in section_keywords:
                            if keyword.upper() == label.upper():
                                continue
                            
                            if any(ignored in keyword for ignored in ignored_headers):
                                continue
                            
                            rects = next_page.search_for(keyword)
                            if rects:
                                avg_y = sum([r.y0 for r in rects]) / len(rects)
                                if avg_y < next_page.rect.height * 0.3:
                                    section_in_top_area = True
                                    found_new_label = True
                                    print(f"[INFO] Halaman {next_page_number}: Section '{keyword}' di atas → stop")
                                    break
                                else:
                                    next_section_y = min([r.y0 for r in rects])
                                    found_new_label = True
                                    section_in_top_area = False
                                    print(f"[INFO] Halaman {next_page_number}: Section '{keyword}' di tengah → crop partial")
                                    break

                    # Decision logic
                    if found_new_label and section_in_top_area:
                        print(f"[INFO] Stop continuation")
                        break

                    elif found_new_label and not section_in_top_area and next_section_y:
                        crop_box = fitz.Rect(0, 0, next_page.rect.width, next_section_y - 30)
                        crop_text = next_page.get_textbox(crop_box).upper()
                        
                        non_foto_validation = [
                            "DATA PERIZINAN", "DATA KAWASAN", "DATA SPLITTER", 
                            "DATA HH EKSISTING", "DATA HH BARU", "DATA TIANG",
                            "BOQ", "LIST ITEM", "BERITA ACARA",
                            "DOKUMENTASI FOTO PROVISIONING"
                        ]
                        
                        if any(kw in crop_text for kw in non_foto_validation):
                            print(f"[SKIP] Area berisi section non-foto")
                            break
                        
                        cont_pix = next_page.get_pixmap(clip=crop_box)
                    else:
                        cont_pix = crop_full_page(next_page)

                    # Validasi height
                    min_height = next_page.rect.height * 0.2
                    if cont_pix.height < min_height:
                        print(f"[SKIP] Continuation terlalu kecil")
                        break

                    cont_filename = f"{normalize_name(label)}_hal{next_page_number}.jpg"
                    cont_out_path = os.path.join(output_dir, cont_filename)
                    cont_pix.save(cont_out_path)
                    print(f"[OK] Continuation '{label}' → {cont_out_path}")

                    results.append({"jenis": label, "patch_foto": cont_out_path})
                    
                    if not (found_new_label and not section_in_top_area):
                        processed_label_per_page[next_page_num] = label

                    if found_new_label and not section_in_top_area:
                        break

                    next_page_num += 1

                break

    doc.close()
    print(f"\n[INFO] ✓ Selesai ekstraksi. Total gambar: {len(results)}")
    return results