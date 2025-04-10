# PDF Extraction API

A simple Flask API that extracts text from PDF files using PyPDF2.

## Features

- Extracts text from PDF files using PyPDF2
- Accepts base64-encoded PDF data via REST API
- CORS enabled for cross-origin requests
- Fallback method if the primary extraction fails
- Comprehensive error handling and logging

## Deployment to Render

1. Create a new Web Service on Render
2. Connect to your repository
3. Configure the service:
   - **Name**: pdf-extraction-api (or your preferred name)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (or paid plans for better performance)

## API Usage

### Extract Text from PDF

**Endpoint**: `POST /extract-pdf`

**Request Body**:
```json
{
  "pdf": "base64EncodedPdfContentHere"
}
```

**Response**:
```json
{
  "text": "Extracted text content from the PDF",
  "characters": 1234
}
```

**Error Response**:
```json
{
  "error": "Error message describing what went wrong"
}
```

## Local Development

1. Create a virtual environment: `python -m venv venv`
2. Activate it:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the server: `python app.py`
5. The API will be available at `http://localhost:10000`

## Testing

Test the API with curl:

```bash
curl -X POST http://localhost:10000/extract-pdf \
  -H "Content-Type: application/json" \
  -d '{"pdf":"base64EncodedPdfContentHere"}'
``` 