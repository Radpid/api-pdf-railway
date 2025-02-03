from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app)

@app.route('/test', methods=['GET', 'POST', 'OPTIONS'])
def test():
    return jsonify({"message": "Test successful"})

@app.route("/", methods=['GET'])
def home():
    return jsonify({"status": "API is running"})

@app.route("/list-pdfs", methods=['POST'])
def list_pdfs():
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        
        # Initialiser Drive
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=['https://www.googleapis.com/auth/drive.readonly'])
        
        service = build('drive', 'v3', credentials=credentials)

        # Lister les PDFs
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
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
