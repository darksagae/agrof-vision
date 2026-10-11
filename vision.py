import base64
import cv2
import numpy as np
MAX_BYTES = 4 * 1024 * 1024

def analyze(raw):
    if not raw or len(raw) > MAX_BYTES: raise ValueError('Use a JPEG or PNG smaller than 4 MB')
    if not (raw.startswith(b'\xff\xd8\xff') or raw.startswith(b'\x89PNG\r\n\x1a\n')): raise ValueError('JPEG or PNG required')
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if image is None: raise ValueError('Image could not be decoded')
    h, w = image.shape[:2]
    if h < 64 or w < 64: raise ValueError('Image must be at least 64 by 64 pixels')
    if h * w > 16000000: raise ValueError('Image exceeds 16 megapixels')
    scale = min(1, 1024 / max(h, w))
    if scale < 1: image = cv2.resize(image, (round(w * scale), round(h * scale)))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([25, 35, 25]), np.array([95, 255, 255]))
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    coverage = float(np.count_nonzero(mask) / mask.size)
    brightness = float(gray.mean())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    annotated = image.copy()
    cv2.drawContours(annotated, [c for c in contours if cv2.contourArea(c) > mask.size * .005], -1, (0, 255, 255), 2)
    issues=[]
    if brightness < 40 or brightness > 230: issues.append('Retake with even lighting')
    if blur < 60: issues.append('Image may be blurry; steady the camera')
    if coverage < .1: issues.append('No substantial green leaf region detected')
    ok, encoded=cv2.imencode('.jpg',annotated,[cv2.IMWRITE_JPEG_QUALITY,80])
    if not ok: raise ValueError('Could not generate preview')
    return {'opencv_version':cv2.__version__, 'original_size':{'width':w,'height':h}, 'green_coverage':round(coverage,3), 'brightness':round(brightness,1), 'focus_score':round(blur,1), 'issues':issues, 'quality_gate_passed':not issues, 'preview':'data:image/jpeg;base64,'+base64.b64encode(encoded).decode(), 'interpretation':'Green segmentation and capture quality only. This does not identify crop species, disease or treatment.'}
