from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import fitz
import logging
from langchain_groq import ChatGroq

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
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
            _, done = downloader.next_chunk()
        
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
        return "\n\n".join(text)
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        raise

@app.route('/extract-text', methods=['POST', 'OPTIONS'])
def extract_text():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400

        file_id = data['file_id']
        logger.info(f"Processing file_id: {file_id}")

        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        logger.info(f"Extracted text length: {len(text)}")

        response = jsonify({
            "status": "success",
            "text": text,
            "total_length": len(text)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        logger.error(f"Error in extract_text: {str(e)}")
        error_response = jsonify({
            "status": "error",
            "error": str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/query', methods=['POST', 'OPTIONS'])
def query_pdf():
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    try:
        data = request.get_json()
        if not data or 'file_id' not in data or 'question' not in data:
            return jsonify({"error": "file_id and question are required"}), 400

        file_id = data['file_id']
        question = data['question']
        logger.info(f"Processing file_id: {file_id} with question: {question}")

        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="mixtral-8x7b-32768"
        )

        prompt = f"""Utilise le contexte suivant pour répondre à la question. 
        Si tu ne trouves pas la réponse dans le contexte, dis-le simplement.
        
        Contexte: {text}
        
        Question: {question}
        """

        response = llm.invoke(prompt)
        logger.info("Got response from Groq")

        api_response = jsonify({
            "status": "success",
            "response": response.content,
            "context_length": len(text)
        })
        api_response.headers.add('Access-Control-Allow-Origin', '*')
        return api_response

    except Exception as e:
        logger.error(f"Error in query_pdf: {str(e)}")
        error_response = jsonify({
            "status": "error",
            "error": str(e)
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/')
def home():
    response = jsonify({"status": "API is running"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
