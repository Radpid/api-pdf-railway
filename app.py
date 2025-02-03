from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/test', methods=['GET', 'POST', 'OPTIONS'])
def test():
    return jsonify({"message": "Test successful"})

@app.route("/", methods=['GET'])
def home():
    return jsonify({"status": "API is running"})

if __name__ == "__main__":
    app.run(debug=True)
