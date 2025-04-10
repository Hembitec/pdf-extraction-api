from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import io
import base64
import logging
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "PDF Extraction API is running",
        "usage": "Send a POST request to /extract-pdf with a base64-encoded PDF",
        "version": "1.0.0"
    })

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    try:
        # Check if request has JSON data
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Request must be JSON with a base64-encoded PDF"}), 400
        
        # Get base64 encoded PDF from request
        pdf_base64 = request.json.get('pdf')
        if not pdf_base64:
            logger.error("No PDF data found in request")
            return jsonify({"error": "No PDF data found in request"}), 400
        
        logger.info("Received PDF extraction request. Processing...")
        
        try:
            # Decode the base64 string
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception as e:
            logger.error(f"Failed to decode base64: {e}")
            return jsonify({"error": "Invalid base64 encoding"}), 400
        
        # Extract text using PyPDF2
        text = ""
        
        # Method 1: Using BytesIO (memory-based)
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PyPDF2.PdfReader(pdf_file)
            
            logger.info(f"PDF has {len(reader.pages)} pages")
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
                else:
                    logger.warning(f"No text extracted from page {i+1}")
        
        except Exception as e:
            # If Method 1 fails, try Method 2 with temporary file
            logger.warning(f"BytesIO method failed: {e}. Trying temp file method.")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf.write(pdf_bytes)
                temp_path = temp_pdf.name
            
            try:
                with open(temp_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    logger.info(f"PDF has {len(reader.pages)} pages (temp file method)")
                    
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                        else:
                            logger.warning(f"No text extracted from page {i+1}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        if not text.strip():
            logger.warning("No text extracted from PDF")
            return jsonify({
                "text": "",
                "warning": "No text could be extracted from the PDF"
            })
            
        logger.info(f"Successfully extracted {len(text)} characters")
        
        return jsonify({
            "text": text,
            "characters": len(text)
        })
        
    except Exception as e:
        logger.error(f"PDF extraction error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False) 