import os
import json
from flask import Flask, jsonify

app = Flask(__name__)

# Charger les credentials Google depuis les variables d’environnement
google_credentials_json = os.getenv("GOOGLE_CREDENTIALS")

if google_credentials_json:
    credentials_dict = json.loads(google_credentials_json)
    # Ici tu peux initialiser Google API avec credentials_dict si nécessaire
else:
    raise ValueError("Les credentials Google ne sont pas définies !")

@app.route("/")
def home():
    return jsonify({"message": "Hello from Vercel!"})

# Point d'entrée Vercel
def handler(request, *args, **kwargs):
    return app(request.environ, start_response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
