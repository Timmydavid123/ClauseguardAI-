import os
import anthropic
import json
import re
import io
import logging
from django.conf import settings
import docx

# Set up logging
logger = logging.getLogger(__name__)

# Try importing PDF libraries with fallbacks
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available")

SYSTEM_PROMPT = """You are an expert contract lawyer and risk analyst.
Analyze contracts and identify risks for the signing party.
Always respond with valid JSON only. No markdown, no explanation outside the JSON."""

ANALYSIS_PROMPT = """Analyze the following contract and return a JSON object with this exact structure:

{
  "overall_risk_score": <number 1-100>,
  "overall_risk_level": "<Low|Medium|High|Critical>",
  "summary": "<2-3 sentence plain English summary>",
  "party_info": {
    "document_type": "<type of contract>",
    "key_parties": "<parties involved>"
  },
  "risks": [
    {
      "id": "<risk_1, risk_2 etc>",
      "title": "<short title>",
      "severity": "<Low|Medium|High|Critical>",
      "category": "<Liability|Payment|Termination|IP|Privacy|Non-compete|Indemnification|Other>",
      "clause": "<exact problematic clause, max 200 chars>",
      "explanation": "<plain English explanation>",
      "recommendation": "<what to do>"
    }
  ],
  "missing_protections": [
    {
      "title": "<missing clause>",
      "importance": "<Low|Medium|High>",
      "explanation": "<why needed>"
    }
  ],
  "positive_clauses": [
    {
      "title": "<favorable clause>",
      "explanation": "<why it benefits you>"
    }
  ],
  "quick_stats": {
    "total_risks": <number>,
    "critical_risks": <number>,
    "high_risks": <number>,
    "medium_risks": <number>,
    "low_risks": <number>
  }
}

Contract text:
"""

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF with multiple fallback methods."""
    text = ""
    errors = []
    
    # Method 1: Try pdfplumber first (better formatting)
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages_text.append(page_text)
                text = "\n".join(pages_text)
                if text.strip():
                    logger.info(f"Successfully extracted {len(text)} chars with pdfplumber")
                    return text.strip()
        except Exception as e:
            error_msg = f"pdfplumber failed: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
    
    # Method 2: Try PyPDF2 as fallback
    if PYPDF2_AVAILABLE:
        try:
            from PyPDF2 import PdfReader
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            
            # Check if encrypted
            if pdf_reader.is_encrypted:
                try:
                    pdf_reader.decrypt('')
                except:
                    raise Exception("PDF is password protected")
            
            pages_text = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages_text.append(page_text)
            
            text = "\n".join(pages_text)
            if text.strip():
                logger.info(f"Successfully extracted {len(text)} chars with PyPDF2")
                return text.strip()
        except Exception as e:
            error_msg = f"PyPDF2 failed: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
    
    # If we get here, both methods failed
    if not text.strip():
        error_details = "; ".join(errors)
        raise Exception(f"Could not extract text from PDF. Tried pdfplumber and PyPDF2. Errors: {error_details}")
    
    return text.strip()

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX files."""
    try:
        if isinstance(file_bytes, bytes):
            file_obj = io.BytesIO(file_bytes)
        else:
            file_obj = file_bytes
        
        d = docx.Document(file_obj)
        text = "\n".join(p.text for p in d.paragraphs).strip()
        
        if not text:
            raise Exception("No text found in DOCX file")
        
        return text
    except Exception as e:
        logger.error(f"DOCX extraction error: {str(e)}")
        raise Exception(f"Failed to extract text from DOCX: {str(e)}")

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from TXT files."""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                text = file_bytes.decode(encoding, errors='ignore').strip()
                if text:
                    logger.info(f"Successfully decoded TXT with {encoding}")
                    return text
            except:
                continue
        
        # Fallback: ignore all errors
        text = file_bytes.decode('utf-8', errors='ignore').strip()
        return text
    except Exception as e:
        logger.error(f"TXT extraction error: {str(e)}")
        raise Exception(f"Failed to extract text from TXT: {str(e)}")

def extract_text_from_file(file, filename: str) -> str:
    """Extract text from various file types with better error handling."""
    ext = os.path.splitext(filename)[1].lower()
    logger.info(f"Extracting text from {filename} (extension: {ext})")

    # Read bytes
    try:
        if hasattr(file, 'read'):
            # For InMemoryUploadedFile or file-like objects
            file_bytes = file.read()
            # Reset file pointer for potential future reads
            if hasattr(file, 'seek'):
                file.seek(0)
        else:
            file_bytes = file
    except Exception as e:
        logger.error(f"Failed to read file: {str(e)}")
        raise Exception(f"Could not read file: {str(e)}")

    if not file_bytes:
        raise Exception("File is empty")

    try:
        if ext == ".pdf":
            return extract_text_from_pdf(file_bytes)
        elif ext == ".docx":
            return extract_text_from_docx(file_bytes)
        elif ext == ".txt":
            return extract_text_from_txt(file_bytes)
        elif ext == ".doc":
            # For old .doc files, try to read as text (limited support)
            try:
                return extract_text_from_txt(file_bytes)
            except:
                raise Exception("Legacy .doc files are not fully supported. Please save as .docx or .txt")
        elif ext == ".rtf":
            # RTF files can sometimes be read as text
            try:
                text = extract_text_from_txt(file_bytes)
                # Remove RTF formatting (very basic)
                text = re.sub(r'{\\.*?}', '', text)
                text = re.sub(r'\\.*?;', '', text)
                return text.strip()
            except:
                raise Exception("RTF extraction failed. Please save as .txt or .docx")
        elif ext == ".odt":
            raise Exception("ODT files are not supported yet. Please save as .docx or .txt")
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except Exception as e:
        logger.error(f"Extraction error for {filename}: {str(e)}")
        raise

def analyze_contract(contract_text: str) -> dict:
    """Analyze contract text using Anthropic API."""
    if not contract_text or len(contract_text.strip()) < 100:
        raise ValueError("Contract text too short (minimum 100 characters)")
    
    try:
        client = anthropic.Anthropic(api_key=settings.AI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {str(e)}")
        raise Exception("AI service configuration error")
    
    # Trim text to avoid token limits
    trimmed = contract_text[:15000]  # Increased to 15k chars
    
    model = os.getenv("ANTHROPIC_MODEL")  # Default to haiku
    if not model:
        model = "claude-3-haiku-20240307"  # Fallback default
    
    logger.info(f"Using Anthropic model: {model}")
    
    try:
        message = client.messages.create(
            model=model,
            max_tokens=4000,
            temperature=0.1,  # Add temperature for more consistent results
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': ANALYSIS_PROMPT + trimmed}]
        )
        
        raw = message.content[0].text.strip()
        logger.debug(f"Raw API response: {raw[:500]}...")
        
        # Clean up JSON formatting
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        raw = raw.strip()
        
        # Parse JSON
        result = json.loads(raw)
        
        # Validate required fields
        required_fields = ['overall_risk_score', 'overall_risk_level', 'summary', 'risks']
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required field in response: {field}")
                result[field] = [] if field == 'risks' else ('Unknown' if field == 'overall_risk_level' else 0)
        
        # Ensure quick_stats is present
        if 'quick_stats' not in result:
            risks = result.get('risks', [])
            result['quick_stats'] = {
                'total_risks': len(risks),
                'critical_risks': sum(1 for r in risks if r.get('severity') == 'Critical'),
                'high_risks': sum(1 for r in risks if r.get('severity') == 'High'),
                'medium_risks': sum(1 for r in risks if r.get('severity') == 'Medium'),
                'low_risks': sum(1 for r in risks if r.get('severity') == 'Low'),
            }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {str(e)}")
        logger.error(f"Raw response: {raw}")
        raise Exception("AI returned invalid JSON. Please try again.")
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise Exception(f"Analysis failed: {str(e)}")