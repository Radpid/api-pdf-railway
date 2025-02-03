from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from PyPDF2 import PdfReader

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "expose_headers": ["Content-Type"],
        "max_age": 600,
        "supports_credentials": False
    }
})

def init_drive_service():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    return build('drive', 'v3', credentials=credentials)

def get_pdf_content(service, file_id):
    request = service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        _, done = downloader.next_chunk()
    
    file.seek(0)
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

@app.route('/test-cors', methods=['OPTIONS'])
@cross_origin()
def handle_options():
    return '', 200

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
@cross_origin()
def extract_text():
    if request.method == "OPTIONS":
        return '', 200
        
    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400
            
        file_id = data['file_id']
        
        # Test de connexion à Drive
        service = init_drive_service()
        if not service:
            return jsonify({"error": "Failed to initialize Drive service"}), 500
            
        # Extraction du texte
        text = get_pdf_content(service, file_id)
        if not text:
            return jsonify({"error": "No text extracted"}), 404

        return jsonify({
            "status": "success",
            "text": text[:1000],
            "total_length": len(text)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "details": "Error during text extraction"
        }), 500

@app.route('/test', methods=['GET'])
@cross_origin()
def test():
    return jsonify({"message": "Test successful"})

if __name__ == "__main__":
    app.run(debug=True)
