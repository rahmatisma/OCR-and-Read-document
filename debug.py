from main import save_output
from readers.pdf_reader import read_pdf 

if __name__ == "__main__":
    file_path = "input/pdf/instalasi.pdf"
    result = read_pdf(file_path)
    base_name = "tes"
    save_output(result, base_name)
