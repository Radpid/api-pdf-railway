from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import fitz  # PyMuPDF
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration CORS plus simple
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

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
        while not done:
            _, done = downloader.next_chunk()  # Correction de la syntaxe ici
        
        file.seek(0)
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
        
        total_pages = len(pdf_document)
        logger.info(f"PDF has {total_pages} pages")
        
        text = []
        for page_num in range(total_pages):
            logger.info(f"Processing page {page_num + 1}/{total_pages}")
            page = pdf_document[page_num]
            text.append(page.get_text())
        
        pdf_document.close()
        return "\n\n".join(text)  # Joins all pages with double newlines
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        raise

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
@cross_origin()
def extract_text():
    if request.method == "OPTIONS":
        return {"message": "ok"}, 200

    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400

        file_id = data['file_id']
        logger.info(f"Processing file_id: {file_id}")

        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        logger.info(f"Extracted text length: {len(text)}")

        return jsonify({
            "status": "success",
            "text": text,  # Sending complete text
            "total_length": len(text)
        })

    except Exception as e:
        logger.error(f"Error in extract_text: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/')
@cross_origin()
def home():
    return jsonify({"status": "API is running"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
