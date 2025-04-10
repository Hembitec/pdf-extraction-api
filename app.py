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
        "message": "PDF & Image Extraction API is running",
        "usage": "Send a POST request to /extract-pdf with a base64-encoded PDF or image",
        "features": ["Regular text extraction", "OCR for scanned documents and images"],
        "supported_formats": ["PDF", "JPG", "JPEG", "PNG", "BMP", "TIFF"],
        "version": "1.2.0"
    })

def extract_text_with_ocr(file_bytes, is_image=False):
    """Extract text from PDF or image using OCR"""
    logger.info(f"Starting OCR extraction process for {'image' if is_image else 'PDF'}")
    text = ""
    
    try:
        # If it's already an image, process it directly
        if is_image:
            logger.info("Processing direct image with OCR")
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
                temp_img.write(file_bytes)
                temp_path = temp_img.name
            
            try:
                # Open the image and extract text
                image = Image.open(temp_path)
                page_text = pytesseract.image_to_string(image)
                if page_text:
                    text += page_text
                else:
                    logger.warning(f"No text extracted from image with OCR")
                
                # Clean up temp file
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Error processing image with OCR: {e}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
        else:
            # For PDFs, convert to images first
            with tempfile.TemporaryDirectory() as temp_dir:
                # Convert PDF to images
                logger.info("Converting PDF to images")
                images = convert_from_bytes(
                    file_bytes, 
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

def is_image_data(file_data, file_type=None):
    """Check if data is an image based on content or explicit file_type"""
    if file_type:
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']
        return file_type.lower() in image_extensions
    
    # Check magic bytes (signatures) for common image formats
    # JPG
    if file_data.startswith(b'\xff\xd8\xff'):
        return True
    # PNG
    if file_data.startswith(b'\x89PNG\r\n\x1a\n'):
        return True
    # BMP
    if file_data.startswith(b'BM'):
        return True
    # GIF
    if file_data.startswith(b'GIF87a') or file_data.startswith(b'GIF89a'):
        return True
    # TIFF
    if file_data.startswith(b'II*\x00') or file_data.startswith(b'MM\x00*'):
        return True
    
    return False

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    try:
        # Check if request has JSON data
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Request must be JSON with a base64-encoded file"}), 400
        
        # Get base64 encoded PDF or image from request
        file_base64 = request.json.get('pdf')
        if not file_base64:
            logger.error("No file data found in request")
            return jsonify({"error": "No file data found in request"}), 400
        
        # Get OCR preference (default to auto)
        ocr_mode = request.json.get('ocr_mode', 'auto')  # Options: 'auto', 'force', 'disable'
        file_type = request.json.get('file_type', '').lower()  # Optional file type hint
        
        logger.info(f"Received extraction request. OCR mode: {ocr_mode}, File type: {file_type or 'not specified'}. Processing...")
        
        try:
            # Decode the base64 string
            file_bytes = base64.b64decode(file_base64)
        except Exception as e:
            logger.error(f"Failed to decode base64: {e}")
            return jsonify({"error": "Invalid base64 encoding"}), 400
        
        # Check if it's an image
        is_image = is_image_data(file_bytes, file_type)
        if is_image:
            logger.info("Detected image file. Will use OCR for extraction.")
            try:
                # Extract text using OCR
                text = extract_text_with_ocr(file_bytes, is_image=True)
                
                logger.info(f"Successfully extracted {len(text)} characters from image using OCR")
                
                return jsonify({
                    "text": text,
                    "characters": len(text),
                    "used_ocr": True,
                    "file_type": "image"
                })
            except Exception as e:
                logger.error(f"Error extracting text from image: {e}")
                return jsonify({"error": f"Failed to extract text from image: {str(e)}"}), 500
        
        # If not an image, process as PDF
        regular_text = ""
        ocr_text = ""
        used_ocr = False
        
        # Standard text extraction
        if ocr_mode != 'force':
            try:
                pdf_file = io.BytesIO(file_bytes)
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
                ocr_text = extract_text_with_ocr(file_bytes)
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
                "used_ocr": used_ocr,
                "file_type": "pdf"
            })
            
        logger.info(f"Successfully extracted {len(final_text)} characters")
        
        return jsonify({
            "text": final_text,
            "characters": len(final_text),
            "used_ocr": used_ocr,
            "file_type": "pdf"
        })
        
    except Exception as e:
        logger.error(f"Extraction error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False) 