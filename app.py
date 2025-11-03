from flask import Flask, request, jsonify
import os
import tempfile
from main import pengecekan_file

app = Flask(__name__)

@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    # Ambil file dari request Laravel
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    try:
        # Simpan file sementara di direktori temp (otomatis dihapus setelah restart)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        # Jalankan pipeline dari main.py
        pengecekan_file(tmp_path)

        # Ambil nama dasar file (tanpa ekstensi)
        base_name = os.path.splitext(os.path.basename(file.filename))[0]
        output_path = os.path.join("output/json", base_name + ".json")

        if not os.path.exists(output_path):
            return jsonify({'error': 'Output JSON not found'}), 500

        # Baca hasil JSON
        with open(output_path, "r", encoding="utf-8") as f:
            data = f.read()

        return jsonify({
            "message": "PDF processed successfully",
            "output_file": output_path,
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
