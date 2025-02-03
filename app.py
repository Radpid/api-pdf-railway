from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from PyPDF2 import PdfReader

app = Flask(__name__)
CORS(app)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Test successful"})

@app.route("/list-pdfs", methods=['POST'])
def list_pdfs():
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        
        service = init_drive_service()
        
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        return jsonify({
            "status": "success",
            "files": [{"id": f["id"], "name": f["name"]} for f in files]
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/extract-text", methods=['POST'])
def extract_text():
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        return jsonify({
            "status": "success",
            "text": text[:1000],  # Retourne les 1000 premiers caractères pour test
            "total_length": len(text)
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

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

if __name__ == "__main__":
    app.run(debug=True)
