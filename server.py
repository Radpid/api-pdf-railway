import fitz  # PyMuPDF pour extraire du texte des PDF
import chromadb
from googleapiclient.discovery import build
from google.oauth2 import service_account
from flask import Flask, request, jsonify
import os

# 🔹 Configuration Google Drive via Railway (clé stockée en variable d’environnement)
SERVICE_ACCOUNT_FILE = "service-account.json"

# Créer le fichier JSON avec les infos de Railway
with open(SERVICE_ACCOUNT_FILE, "w") as f:
    f.write(os.getenv("GOOGLE_CREDENTIALS", "{}"))

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build("drive", "v3", credentials=creds)

# 🔹 Fonction pour extraire le texte d'un PDF depuis Google Drive
def get_pdf_text(file_id):
    request = drive_service.files().get_media(fileId=file_id)
    
    with open("temp.pdf", "wb") as f:
        f.write(request.execute())

    doc = fitz.open("temp.pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    return text

# 🔹 Création du serveur Flask
app = Flask(__name__)

@app.route("/search", methods=["POST"])
def search():
    user_query = request.json["query"]
    file_id = os.getenv("PDF_FILE_ID")  # ID du fichier Google Drive

    if not file_id:
        return jsonify({"error": "PDF_FILE_ID non défini"}), 400

    pdf_text = get_pdf_text(file_id)

    if user_query.lower() in pdf_text.lower():
        return jsonify({"answer": "Oui, cette information est présente dans le PDF."})
    return jsonify({"answer": "Je n’ai pas trouvé cette information."})

@app.route("/", methods=["GET"])
def home():
    return "API PDF sur Railway fonctionne ! 🚀"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
