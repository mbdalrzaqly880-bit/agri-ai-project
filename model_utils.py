# ==============================================================================
# model/model_utils.py
# ==============================================================================
# نستخدم tflite-runtime بدل TensorFlow الكامل - أخف بكثير بالذاكرة والحجم،
# مناسب للاستضافة على خطط مجانية محدودة الموارد (Render Free Tier)
# ==============================================================================

import os
import json
import colorsys
import numpy as np
import requests
from PIL import Image

from utils.treatment_lookup import get_treatment

try:
    from tflite_runtime.interpreter import Interpreter
except ImportError:
    from tensorflow.lite.python.interpreter import Interpreter

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, 'fruit_model.tflite')
CLASS_NAMES_PATH = os.path.join(MODEL_DIR, 'class_names.json')

# ------------------------------------------------------------------------------
# رابط تحميل الموديل من OneDrive - نستخدمه فقط لو الملف غير موجود محلياً
# (مفيد جداً وقت النشر على Render، لأن ملف الموديل ما رفعناه لـ GitHub
# بسبب صعوبة الرفع من الجوال بإنترنت ضعيف - نحمّله من هنا بدلاً منه)
# ------------------------------------------------------------------------------
MODEL_DOWNLOAD_URL = (
    "https://1drv.ms/u/c/CF3177BCED0F8390/"
    "IQC0ImDFXipCRrzjYRt12bzrAauPFr1goHqY2BtJyQccdFM?download=1"
)


def _ensure_model_downloaded():
    """
    تتأكد إن ملف الموديل موجود محلياً، وإلا تحمّله تلقائياً من OneDrive.
    تشتغل هذي الدالة مرة وحدة بس (أول ما السيرفر يحتاج الموديل لأول مرة).
    """
    if os.path.exists(MODEL_PATH):
        return  # الملف موجود أصلاً، ما نحتاج نحمّله مرة ثانية

    print("جاري تحميل ملف الموديل من OneDrive (أول مرة فقط)...")

    # stream=True يخلينا نحمّل الملف على دفعات (chunks) بدل ما نحمّله
    # كامل بالذاكرة دفعة وحدة - أفضل للملفات الكبيرة ولاستقرار الاتصال
    response = requests.get(MODEL_DOWNLOAD_URL, stream=True, timeout=60)
    response.raise_for_status()  # يرمي خطأ واضح لو فشل التحميل

    with open(MODEL_PATH, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print("تم تحميل الموديل بنجاح!")

FRUIT_NAME_AR = {
    "apple": "تفاح", "banana": "موز", "orange": "برتقال", "mango": "مانجو",
    "grape": "عنب", "pomegranate": "رمان", "guava": "جوافة", "strawberry": "فراولة",
}

RIPENESS_HUE_RANGES = {
    "banana": (40, 65), "mango": (30, 60), "orange": (20, 45),
    "pomegranate": (0, 20), "strawberry": (0, 15), "apple": (0, 40),
}

RIPENESS_NOT_SUPPORTED = ["grape", "guava"]

_interpreter = None
_input_details = None
_output_details = None
_class_names = None


def _load_resources():
    global _interpreter, _input_details, _output_details, _class_names

    if _interpreter is None:
        # نتأكد أول من وجود الملف، ونحمّله تلقائياً من OneDrive لو ناقص
        _ensure_model_downloaded()

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "تعذّر تحميل ملف fruit_model.tflite - تأكد من صحة رابط OneDrive."
            )
        _interpreter = Interpreter(model_path=MODEL_PATH)
        _interpreter.allocate_tensors()
        _input_details = _interpreter.get_input_details()
        _output_details = _interpreter.get_output_details()

    if _class_names is None:
        with open(CLASS_NAMES_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            _class_names = {int(k): v for k, v in raw.items()}


def _parse_label(label):
    parts = label.split('_')
    fruit_key = parts[0].lower()
    status = parts[-1].lower()
    is_healthy = (status == 'healthy')
    return fruit_key, is_healthy


def _estimate_ripeness(image_path, fruit_key):
    if fruit_key in RIPENESS_NOT_SUPPORTED:
        return "غير محددة (يصعب تقديرها من اللون لهذا النوع)"
    if fruit_key not in RIPENESS_HUE_RANGES:
        return "غير محددة"

    img = Image.open(image_path).convert('RGB').resize((100, 100))
    pixels = np.array(img) / 255.0
    h, w, _ = pixels.shape
    margin_h, margin_w = int(h * 0.2), int(w * 0.2)
    center_region = pixels[margin_h:h - margin_h, margin_w:w - margin_w]
    avg_r, avg_g, avg_b = center_region.reshape(-1, 3).mean(axis=0)
    hue, _, _ = colorsys.rgb_to_hsv(avg_r, avg_g, avg_b)
    hue_degrees = hue * 360
    low, high = RIPENESS_HUE_RANGES[fruit_key]
    return "ناضجة" if (low <= hue_degrees <= high) else "غير ناضجة"


def predict_fruit(image_path):
    _load_resources()

    img = Image.open(image_path).convert('RGB').resize((224, 224))
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    _interpreter.set_tensor(_input_details[0]['index'], img_array)
    _interpreter.invoke()
    predictions = _interpreter.get_tensor(_output_details[0]['index'])[0]

    predicted_index = int(np.argmax(predictions))
    confidence = round(float(predictions[predicted_index]) * 100, 1)

    raw_label = _class_names[predicted_index]
    fruit_key, is_healthy = _parse_label(raw_label)
    fruit_type_ar = FRUIT_NAME_AR.get(fruit_key, fruit_key.capitalize())
    ripeness = _estimate_ripeness(image_path, fruit_key)

    result = {
        'fruit_type': fruit_type_ar,
        'ripeness': ripeness,
        'is_healthy': is_healthy,
        'confidence': confidence,
    }

    if not is_healthy:
        result['disease_name'] = f'فساد/تلف في ثمرة {fruit_type_ar}'
        result['treatment'] = get_treatment(fruit_key)

    return result
