from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import fitz  # PyMuPDF est plus robuste que PyPDF2
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration CORS globale
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
    }
})

def init_drive_service():
    try:
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if not credentials_json:
            raise Exception("Google credentials not found")
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=['https://www.googleapis.com/auth/drive.readonly'])
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Error initializing Drive service: {str(e)}")
        raise

def get_pdf_content(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()
        
        file.seek(0)
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
        
        text = ""
        for page_num in range(len(pdf_document)):
            text += pdf_document[page_num].get_text()
        
        pdf_document.close()
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        raise

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
def extract_text():
    # Log la requête
    logger.info(f"Received {request.method} request to /extract-text")
    logger.debug(f"Headers: {dict(request.headers)}")

    # Gestion explicite de OPTIONS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400

        file_id = data['file_id']
        logger.info(f"Processing file_id: {file_id}")

        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        response = jsonify({
            "status": "success",
            "text": text[:1000],  # Premier 1000 caractères
            "total_length": len(text)
        })
        return response

    except Exception as e:
        logger.error(f"Error in extract_text: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/test', methods=['GET'])
def test():
    response = jsonify({"message": "Test successful"})
    return response

if __name__ == "__main__":
    app.run(debug=True)
