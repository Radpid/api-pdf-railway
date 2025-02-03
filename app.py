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
CORS(app)

# Configurations
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def init_drive_service():
    """Initialise le service Google Drive"""
    try:
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if not credentials_json:
            raise ValueError("Google credentials not found in environment variables")
        
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=SCOPES)
        
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        raise Exception(f"Failed to initialize Drive service: {str(e)}")

def get_pdf_content(service, file_id):
    """Extrait le texte d'un fichier PDF depuis Google Drive"""
    try:
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
    except Exception as e:
        raise Exception(f"Failed to extract PDF content: {str(e)}")

@app.route("/")
def home():
    """Point de terminaison racine pour vérifier que l'API fonctionne"""
    return jsonify({
        "status": "running",
        "message": "Welcome to PDF Analysis API"
    })

@app.route("/test")
def test_env():
    """Point de terminaison de test pour vérifier la configuration"""
    try:
        creds = json.loads(os.getenv("GOOGLE_CREDENTIALS", "{}"))
        groq_key = os.getenv("GROQ_API_KEY")
        return jsonify({
            "google_creds_valid": bool(creds),
            "groq_key_present": bool(groq_key)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/query", methods=["POST"])
def query_documents():
    """Point de terminaison principal pour interroger les documents"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        query = data.get("query")
        folder_id = data.get("folder_id")

        if not query or not folder_id:
            return jsonify({"error": "Missing required fields: query and folder_id"}), 400

        # Initialiser le service Drive
        service = init_drive_service()

        # Récupérer tous les PDF du dossier
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        if not files:
            return jsonify({"error": "No PDF files found in the specified folder"}), 404

        # Extraire le contenu de tous les PDFs
        all_text = ""
        for file in files:
            all_text += get_pdf_content(service, file['id'])

        if not all_text.strip():
            return jsonify({"error": "No text content found in PDFs"}), 404

        # Configuration de Groq
        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="mixtral-8x7b-32768"
        )

        # Créer le prompt
        prompt = f"""Utilise le contexte suivant pour répondre à la question. 
        Si tu ne trouves pas la réponse dans le contexte, dis-le simplement.
        
        Contexte: {all_text[:30000]}
        
        Question: {query}
        """

        # Obtenir la réponse
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
