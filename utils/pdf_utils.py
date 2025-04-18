import PyPDF2
import io

def extract_text_from_pdf(file_obj):
    """Extracts text from a PDF file object.

    Args:
        file_obj: A file-like object representing the PDF.

    Returns:
        A string containing the extracted text, or None if extraction fails.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n" # Add newline between pages
        return text.strip() if text else None
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None 