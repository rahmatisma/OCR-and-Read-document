# pipeline utama ocr/penggabungan gambar dan atribut
from .image_extractor import extract_images_from_pdf
from .text_reader import read_image
from .annotator import annotate_result

def process_pdf_images(pdf_path):
    results = []
    image_paths = extract_images_from_pdf(pdf_path)

    for img_path in image_paths:
        text = read_image(img_path)
        annotated = annotate_result({"image_path": img_path, "text": text})
        results.append(annotated)

    return results
