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
    """Initialise et retourne le service Google Drive"""
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
    """Extrait et retourne le contenu texte d'un PDF de Google Drive"""
    try:
        logger.info(f"Starting PDF extraction for file: {file_id}")
        
        # Téléchargement du fichier
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        
        done = False
        while done is False:
            _, done = downloader.next_chunk()
        
        file.seek(0)
        logger.info("File downloaded successfully")

        # Extraction du texte avec PyMuPDF
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
        logger.info(f"PDF opened successfully. Number of pages: {len(pdf_document)}")
        
        text = ""
        for page_num in range(len(pdf_document)):
            logger.info(f"Processing page {page_num + 1}/{len(pdf_document)}")
            page = pdf_document[page_num]
            page_text = page.get_text()
            text += page_text + "\n\n"  # Ajoute des sauts de ligne entre les pages
        
        pdf_document.close()
        logger.info(f"Text extraction completed. Total characters: {len(text)}")
        
        return text
    except Exception as e:
        logger.error(f"Error in PDF extraction: {str(e)}")
        raise

@app.route('/')
def home():
    """Route principale pour vérifier que l'API fonctionne"""
    return jsonify({
        "status": "running",
        "message": "PDF Analysis API is running"
    })

@app.route('/test')
def test():
    """Route de test pour vérifier la configuration CORS"""
    response = jsonify({"message": "Test successful"})
    return response

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
def extract_text():
    """Route pour extraire le texte d'un PDF"""
    logger.info(f"Received {request.method} request to /extract-text")
    logger.debug(f"Headers: {dict(request.headers)}")

    # Gestion des requêtes OPTIONS pour CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        # Validation des données d'entrée
        data = request.get_json()
        if not data or 'file_id' not in data:
            logger.warning("No file_id provided in request")
            return jsonify({"error": "No file_id provided"}), 400

        file_id = data['file_id']
        logger.info(f"Processing file_id: {file_id}")

        # Initialisation du service Drive
        service = init_drive_service()
        
        # Extraction du texte
        text = get_pdf_content(service, file_id)
        
        # Préparation de la réponse
        response = jsonify({
            "status": "success",
            "text": text,
            "total_length": len(text)
        })
        
        return response

    except Exception as e:
        logger.error(f"Error in extract_text: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/info', methods=['POST'])
def get_file_info():
    """Route pour obtenir les informations sur un fichier PDF"""
    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400

        file_id = data['file_id']
        service = init_drive_service()
        
        file = service.files().get(fileId=file_id, fields="name,mimeType,modifiedTime").execute()
        
        return jsonify({
            "status": "success",
            "file_info": {
                "name": file.get('name'),
                "type": file.get('mimeType'),
                "last_modified": file.get('modifiedTime')
            }
        })

    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
