import io
from pypdf import PdfReader

def extract_text_from_stream(stream: io.BytesIO) -> str:
    """
    Extracts text from a PDF byte stream using pypdf.
    """
    try:
        reader = PdfReader(stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"PDF Read Error: {e}")
        return ""
