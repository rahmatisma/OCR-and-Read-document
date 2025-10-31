"""
Debug Wrapper untuk Test Parser Checklist Wireless
Jalankan file ini untuk debug mendalam

Usage:
    python debug_wrapper.py
"""

import fitz
from readers.ocr.processor import process_page_ocr
from parsers.checklist_wireless_parser import parse_checklist_wireless
import json
import re


def debug_ocr_output(pdf_path):
    """Debug OCR output untuk lihat apa yang sebenarnya di-extract"""
    
    print("="*80)
    print("STEP 1: DEBUG OCR OUTPUT")
    print("="*80)
    
    doc = fitz.open(pdf_path)
    page = doc[0]  # Halaman pertama
    
    # Get native text
    native_text = page.get_text("text").strip()
    print(f"\n[1] Native Text Length: {len(native_text)} chars")
    print(f"[1] Has Native Text: {bool(native_text)}")
    
    if native_text:
        print(f"\n[1] Native Text Preview (first 500 chars):")
        print("-" * 80)
        print(native_text[:500])
        print("-" * 80)
    
    # Run OCR
    print(f"\n[2] Running OCR...")
    page_text, ocr_lines = process_page_ocr(page, enhance=False, return_structured=True)
    
    print(f"\n[2] OCR Text Length: {len(page_text)} chars")
    print(f"[2] OCR Lines Count: {len(ocr_lines)}")
    
    print(f"\n[2] OCR Text Preview (first 500 chars):")
    print("-" * 80)
    print(page_text[:500])
    print("-" * 80)
    
    # Show OCR items detail
    if ocr_lines:
        print(f"\n[2] OCR Items Detail (first 20):")
        print("-" * 80)
        for i, item in enumerate(ocr_lines[:20]):
            text = item['text'][:60] + "..." if len(item['text']) > 60 else item['text']
            score = item.get('score', 0)
            pos = item.get('position', (0, 0))
            print(f"  [{i:3d}] score={score:.2f} pos=({pos[0]:.0f},{pos[1]:.0f}) | {text}")
        print("-" * 80)
    
    doc.close()
    
    return page_text, ocr_lines


def debug_field_search(all_text, ocr_lines):
    """Debug field search untuk lihat apakah field labels ketemu"""
    
    print("\n" + "="*80)
    print("STEP 2: DEBUG FIELD SEARCH")
    print("="*80)
    
    # Field patterns yang dicari
    fields_to_test = {
        "Nama Pelanggan": r"Nama\s*Pelanggan",
        "Contact Person": r"Contact\s*Person",
        "Alamat": r"^Alamat(?!\s*Email)",
        "Kota": r"^Kota(?!\s*:)",
        "Propinsi": r"Prop(?:i|o)nsi",
        "No. SPK": r"No\.?\s*SPK",
        "Tanggal": r"^Tanggal(?!\s*Survey)",
        "Jam Perintah": r"Jam\s*Perintah",
        "Jam Persiapan": r"Jam\s*Persiapan",
    }
    
    print("\n[A] Regex Search in All Text:")
    print("-" * 80)
    for field_name, pattern in fields_to_test.items():
        match = re.search(pattern, all_text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Get context (50 chars before and after)
            start = max(0, match.start() - 20)
            end = min(len(all_text), match.end() + 80)
            context = all_text[start:end].replace('\n', '\\n')
            print(f"  ✓ {field_name:20s} | Found at pos {match.start():5d} | ...{context}...")
        else:
            print(f"  ✗ {field_name:20s} | NOT FOUND")
    print("-" * 80)
    
    # Search in OCR spatial map
    if ocr_lines:
        print("\n[B] Spatial Search in OCR Lines:")
        print("-" * 80)
        
        for field_name, pattern in fields_to_test.items():
            found = False
            for i, item in enumerate(ocr_lines):
                if re.search(pattern, item['text'], re.IGNORECASE):
                    print(f"  ✓ {field_name:20s} | Found at index {i:3d} | '{item['text']}'")
                    
                    # Show next 3 items
                    for j in range(i+1, min(i+4, len(ocr_lines))):
                        next_item = ocr_lines[j]
                        next_text = next_item['text'][:60] + "..." if len(next_item['text']) > 60 else next_item['text']
                        print(f"       → next[{j-i}]: '{next_text}'")
                    
                    found = True
                    break
            
            if not found:
                print(f"  ✗ {field_name:20s} | NOT FOUND in OCR lines")
        
        print("-" * 80)


def debug_datetime_extraction(all_text):
    """Debug datetime extraction"""
    
    print("\n" + "="*80)
    print("STEP 3: DEBUG DATETIME PATTERNS")
    print("="*80)
    
    # Find all datetime patterns
    datetime_pattern = r'(\d{2}-[A-Za-z]{3}-\d{4})\s*(\d{2}:\d{2})'
    matches = list(re.finditer(datetime_pattern, all_text))
    
    print(f"\nFound {len(matches)} datetime patterns:")
    print("-" * 80)
    for i, match in enumerate(matches):
        date = match.group(1)
        time = match.group(2)
        # Get context
        start = max(0, match.start() - 30)
        end = min(len(all_text), match.end() + 30)
        context = all_text[start:end].replace('\n', ' ')
        print(f"  [{i}] {date} {time} | context: ...{context}...")
    print("-" * 80)


def run_full_debug(pdf_path):
    """Run full debug pipeline"""
    
    print("\n" + "#"*80)
    print("# CHECKLIST WIRELESS PARSER - DEEP DEBUG")
    print("#"*80)
    print(f"PDF: {pdf_path}\n")
    
    # Step 1: Debug OCR
    page_text, ocr_lines = debug_ocr_output(pdf_path)
    
    # Step 2: Debug field search
    debug_field_search(page_text, ocr_lines)
    
    # Step 3: Debug datetime
    debug_datetime_extraction(page_text)
    
    # Step 4: Run parser
    print("\n" + "="*80)
    print("STEP 4: RUN PARSER")
    print("="*80)
    
    result = parse_checklist_wireless(
        all_text=page_text,
        page_texts=[page_text],
        ttd_results={},
        doc_results={},
        ocr_data=ocr_lines
    )
    
    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result


# ===== MAIN =====

if __name__ == "__main__":
    pdf_path = "input/pdf/form checklist maintenance remote wireless.pdf"
    
    result = run_full_debug(pdf_path)
    
    print("\n" + "#"*80)
    print("# DEBUG COMPLETED")
    print("#"*80)