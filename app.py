from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import fitz
import logging

app = Flask(__name__)

# Configuration CORS plus simple mais complète
CORS(app, supports_credentials=True, resources={
    r"/*": {
        "origins": ["http://localhost", "http://127.0.0.1", "*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

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
    pdf_document = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in pdf_document:
        text += page.get_text() + "\n\n"
    pdf_document.close()
    return text

@app.route('/test', methods=['GET', 'OPTIONS'])
def test():
    response = make_response(jsonify({"message": "Test successful"}))
    return response

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
def extract_text():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400

        service = init_drive_service()
        text = get_pdf_content(service, data['file_id'])

        response = make_response(jsonify({
            "status": "success",
            "text": text,
            "total_length": len(text)
        }))
        return response

    except Exception as e:
        response = make_response(jsonify({
            "status": "error",
            "error": str(e)
        }), 500)
        return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
