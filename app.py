import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from PyPDF2 import PdfReader
from langchain_groq import ChatGroq

app = Flask(__name__)

# Configuration CORS simplifiée
CORS(app)

@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "message": "Welcome to PDF Analysis API"
    })

@app.route("/query", methods=["POST", "OPTIONS"])
def query_documents():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        query = data.get("query")
        folder_id = data.get("folder_id")

        if not query or not folder_id:
            return jsonify({"error": "Missing required fields: query and folder_id"}), 400

        # Initialiser Drive
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if not credentials_json:
            return jsonify({"error": "Google credentials not found"}), 500

        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=['https://www.googleapis.com/auth/drive.readonly'])
        
        service = build('drive', 'v3', credentials=credentials)

        # Récupérer les PDFs
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        if not files:
            return jsonify({"error": "No PDF files found"}), 404

        # Extraire le texte
        all_text = ""
        for file in files:
            request = service.files().get_media(fileId=file['id'])
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
            
            file_content.seek(0)
            reader = PdfReader(file_content)
            for page in reader.pages:
                all_text += page.extract_text() or ""

        # Utiliser Groq
        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="mixtral-8x7b-32768"
        )

        prompt = f"""Utilise le contexte suivant pour répondre à la question. 
        Si tu ne trouves pas la réponse dans le contexte, dis-le simplement.
        
        Contexte: {all_text[:30000]}
        
        Question: {query}
        """

        response = llm.invoke(prompt)

        return jsonify({
            "response": response.content,
            "status": "success"
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
