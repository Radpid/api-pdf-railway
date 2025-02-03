@app.route('/extract-text', methods=['POST', 'OPTIONS'])
def extract_text():
    logger.info(f"Received {request.method} request to /extract-text")

    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        data = request.get_json()
        if not data or 'file_id' not in data:
            return jsonify({"error": "No file_id provided"}), 400

        file_id = data['file_id']
        logger.info(f"Processing file_id: {file_id}")

        service = init_drive_service()
        text = get_pdf_content(service, file_id)

        # Envoyer le texte complet, pas juste les 1000 premiers caractères
        response = jsonify({
            "status": "success",
            "text": text,  # Texte complet
            "total_length": len(text)
        })
        return response

    except Exception as e:
        logger.error(f"Error in extract_text: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
