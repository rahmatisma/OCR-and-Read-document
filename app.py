from flask import Flask, request, jsonify
import tempfile
import uuid
from main import pengecekan_file

app = Flask(__name__)

@app.route('/process-pdf', methods=['POST'])
def process_pdf():

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "File not provided"}), 400

    try:
        # simpan sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            pdf_path = tmp.name

        # jalankan pipeline (harus return dict!)
        result = pengecekan_file(pdf_path)

        if not isinstance(result, dict):
            return jsonify({"error": "pengecekan_file must return JSON(dict)"}), 500

        # generate nama output
        json_filename = f"{uuid.uuid4()}.json"

        return jsonify({
            "message": "processed ok",
            "filename": json_filename,
            "data": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
