import os
import json
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import PyPDF2
from langchain_groq import ChatGroq

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def init_drive_service():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    if not credentials_json:
        raise ValueError("Google credentials not found")
    
    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict, scopes=SCOPES)
    
    return build('drive', 'v3', credentials=credentials)

def get_pdf_content(service, file_id):
    request = service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        _, done = downloader.next_chunk()
    
    file.seek(0)
    reader = PyPDF2.PdfReader(file)  # Notez PdfReader au lieu de PdfFileReader
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

@app.route("/")
def home():
    return jsonify({"status": "running"})

@app.route("/test")
def test_env():
    try:
        creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
        groq_key = os.getenv("GROQ_API_KEY")
        return jsonify({
            "google_creds_valid": bool(creds),
            "groq_key_present": bool(groq_key)
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/query", methods=["POST"])
def query_documents():
    try:
        data = request.get_json()
        query = data.get("query")
        folder_id = data.get("folder_id")

        service = init_drive_service()
        
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/pdf'",
            fields="files(id, name)"
        ).execute()
        
        all_text = ""
        for file in results.get('files', []):
            all_text += get_pdf_content(service, file['id'])

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
            "response": response.content
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
