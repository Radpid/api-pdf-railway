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
from langchain_groq import ChatGroq  # Ajout de Groq

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# On garde toutes les fonctions existantes...

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

        # 1. Extraire le texte du PDF
        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        # 2. Utiliser Groq
        llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="deepseek-r1-distill-llama-70b"
        )

        # 3. Créer le prompt
        prompt = f"""Utilise le contexte suivant pour répondre à la question. 
        Si tu ne trouves pas la réponse dans le contexte, dis-le simplement.
        
        Contexte: {text}
        
        Question: {question}
        """

        # 4. Obtenir la réponse
        response = llm.invoke(prompt)

        # 5. Retourner la réponse
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
