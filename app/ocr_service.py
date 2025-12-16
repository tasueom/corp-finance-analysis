"""
OCR 서비스 모듈
이미지 텍스트 추출 담당
"""
import easyocr
import base64
import numpy as np
from PIL import Image
from io import BytesIO


_ocr_reader = None


def get_ocr_reader():
    """EasyOCR Reader를 지연 로딩합니다"""
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(['ko', 'en'], gpu=False)
    return _ocr_reader


def process_image(file):
    """
    이미지 파일을 처리하여 텍스트를 추출합니다.
    
    Args:
        file: 업로드된 파일 객체
    
    Returns:
        tuple: (image_data_uri: str, text_lines: list)
    """
    if not file:
        return None, None
    
    image_bytes = BytesIO()
    file.save(image_bytes)
    image_bytes.seek(0)
    
    image_base64 = base64.b64encode(image_bytes.read()).decode('utf-8')
    image_bytes.seek(0)
    
    file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    mime_type = f'image/{file_ext}' if file_ext in ['jpg', 'jpeg', 'png', 'gif'] else 'image/png'
    image_data_uri = f'data:{mime_type};base64,{image_base64}'
    
    img = Image.open(image_bytes)
    img_array = np.array(img)
    
    reader = get_ocr_reader()
    text_lines = reader.readtext(img_array, detail=0)
    
    return image_data_uri, text_lines

