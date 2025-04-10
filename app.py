from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import io
import base64
import logging
import tempfile
import os

# OCR imports
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

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
        "features": ["Regular text extraction", "OCR for scanned documents"],
        "version": "1.1.0"
    })

def extract_text_with_ocr(pdf_bytes):
    """Extract text from PDF using OCR"""
    logger.info("Starting OCR extraction process")
    text = ""
    
    try:
        # Create temporary directory for images
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert PDF to images
            logger.info("Converting PDF to images")
            images = convert_from_bytes(
                pdf_bytes, 
                output_folder=temp_dir,
                fmt="jpeg",
                dpi=300
            )
            
            logger.info(f"Converted {len(images)} pages to images")
            
            # Process each image with OCR
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1} with OCR")
                # Use pytesseract to extract text
                page_text = pytesseract.image_to_string(image)
                if page_text:
                    text += page_text + "\n\n"
                else:
                    logger.warning(f"No text extracted from page {i+1} with OCR")
            
            logger.info(f"OCR extraction complete, found {len(text)} characters")
            return text
    except Exception as e:
        logger.error(f"Error in OCR process: {e}")
        raise e

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
        
        # Get OCR preference (default to auto)
        ocr_mode = request.json.get('ocr_mode', 'auto')  # Options: 'auto', 'force', 'disable'
        
        logger.info(f"Received PDF extraction request. OCR mode: {ocr_mode}. Processing...")
        
        try:
            # Decode the base64 string
            pdf_bytes = base64.b64decode(pdf_base64)
        except Exception as e:
            logger.error(f"Failed to decode base64: {e}")
            return jsonify({"error": "Invalid base64 encoding"}), 400
        
        # Extract text using PyPDF2 (without OCR)
        regular_text = ""
        ocr_text = ""
        used_ocr = False
        
        # Standard text extraction
        if ocr_mode != 'force':
            try:
                pdf_file = io.BytesIO(pdf_bytes)
                reader = PyPDF2.PdfReader(pdf_file)
                
                logger.info(f"PDF has {len(reader.pages)} pages")
                
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        regular_text += page_text + "\n\n"
                    else:
                        logger.warning(f"No text extracted from page {i+1}")
                
                logger.info(f"Regular extraction found {len(regular_text)} characters")
            except Exception as e:
                logger.warning(f"Regular extraction failed: {e}")
        
        # Decide if OCR is needed
        should_use_ocr = (
            ocr_mode == 'force' or 
            (ocr_mode == 'auto' and (not regular_text.strip() or len(regular_text) < 100))
        )
        
        # Run OCR if needed
        if should_use_ocr:
            logger.info("Using OCR for text extraction")
            try:
                ocr_text = extract_text_with_ocr(pdf_bytes)
                used_ocr = True
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
                # If regular extraction also failed, we have no text
                if not regular_text:
                    return jsonify({"error": "Failed to extract text with both regular and OCR methods"}), 500
        
        # Choose the best text
        final_text = ocr_text if used_ocr and ocr_text.strip() else regular_text
        
        if not final_text.strip():
            logger.warning("No text extracted from PDF")
            return jsonify({
                "text": "",
                "warning": "No text could be extracted from the PDF",
                "used_ocr": used_ocr
            })
            
        logger.info(f"Successfully extracted {len(final_text)} characters")
        
        return jsonify({
            "text": final_text,
            "characters": len(final_text),
            "used_ocr": used_ocr
        })
        
    except Exception as e:
        logger.error(f"PDF extraction error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False) 