import os
import asyncio
import re
from gtts import gTTS
import uuid
import json
from pathlib import Path
from dotenv import load_dotenv

from ai_service import get_complete_story, generate_title_if_missing

# تحميل المتغيرات البيئية
load_dotenv()

# الحصول على مسار تخزين ملفات الصوت
AUDIO_STORAGE_PATH = os.path.abspath(os.getenv("AUDIO_STORAGE_PATH", "./audio_files"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# قاموس لتخزين معرفات الملفات الصوتية للقصص
story_audio_files = {}

def clean_text_for_tts(text: str) -> str:
    """
    تنظيف النص من الرموز التي قد تؤثر على جودة القراءة الصوتية
    """
    # استبدال علامات الترقيم التي قد تسبب مشاكل بمسافات أو استبعادها
    text = re.sub(r'!', ' ', text)  # استبدال علامة التعجب بمسافة
    text = re.sub(r'\?', ' ', text)  # استبدال علامة الاستفهام بمسافة
    text = re.sub(r'[،,]', ' ', text)  # استبدال الفواصل بمسافات
    text = re.sub(r';', ' ', text)  # استبدال الفاصلة المنقوطة بمسافة
    text = re.sub(r':', ' ', text)  # استبدال النقطتين بمسافة
    text = re.sub(r'#', ' ', text)  # استبدال علامة الهاشتاغ بمسافة
    text = re.sub(r'@', ' ', text)  # استبدال علامة الإيميل بمسافة
    text = re.sub(r'_', ' ', text)  # استبدال الشرطة السفلية بمسافة
    text = re.sub(r'\*', ' ', text)  # استبدال علامة النجمة بمسافة
    text = re.sub(r'=', ' ', text)  # استبدال علامة المساواة بمسافة
    text = re.sub(r'\+', ' ', text)  # استبدال علامة الزائد بمسافة
    text = re.sub(r'-', ' ', text)  # استبدال علامة الناقص بمسافة
    text = re.sub(r'/', ' ', text)  # استبدال علامة القسمة بمسافة
    text = re.sub(r'\\', ' ', text)  # استبدال الشرطة المائلة العكسية بمسافة
    text = re.sub(r'%', ' بالمئة ', text)  # استبدال علامة النسبة بكلمة "بالمئة"
    text = re.sub(r'&', ' و ', text)  # استبدال علامة & بكلمة "و"
    text = re.sub(r'\^', ' ', text)  # استبدال علامة القوة بمسافة
    text = re.sub(r'\$', ' ', text)  # استبدال علامة الدولار بمسافة
    
    # إزالة علامات التنصيص تماماً
    text = re.sub(r'["""\'«»]', ' ', text)  # إزالة كل أنواع علامات التنصيص
    
    # إزالة الأقواس والمحتوى بداخلها
    text = re.sub(r'\(.*?\)', ' ', text)
    text = re.sub(r'\[.*?\]', ' ', text)
    text = re.sub(r'\{.*?\}', ' ', text)
    text = re.sub(r'<.*?>', ' ', text)
    
    # تنظيف الفترات الطويلة من المسافات المتكررة الناتجة عن الإزالة
    text = re.sub(r'\s+', ' ', text)
    
    # الحفاظ على النقاط كفواصل بين الجمل مع إضافة مسافة
    text = re.sub(r'\.', '. ', text)
    
    return text.strip()

async def ensure_storage_path():
    """
    التأكد من وجود مجلد لتخزين ملفات الصوت
    """
    Path(AUDIO_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

async def text_to_speech(text: str, filename: str) -> str:
    """
    تحويل النص إلى صوت وحفظه في ملف
    """
    # التأكد من وجود مجلد التخزين
    await ensure_storage_path()
    
    # مسار الملف الكامل
    file_path = os.path.join(AUDIO_STORAGE_PATH, filename)
    
    # التحقق مما إذا كان الملف موجوداً بالفعل
    if os.path.exists(file_path):
        return filename
    
    # تنظيف النص من الرموز التي قد تؤثر على جودة القراءة
    cleaned_text = clean_text_for_tts(text)
    print(f"Original text length: {len(text)}, Cleaned text length: {len(cleaned_text)}")
    
    # استخدام وظيفة run_in_executor لتنفيذ عملية TTS في خيط منفصل
    loop = asyncio.get_event_loop()
    
    await loop.run_in_executor(
        None,
        lambda: gTTS(text=cleaned_text, lang='ar', slow=False).save(file_path)
    )
    
    return filename

async def generate_audio_for_story(story_id: str, speed: float = 1.0) -> str:
    """
    توليد ملف صوتي للقصة الكاملة وإرجاع معرف الملف مع معلومات السرعة
    """
    # التحقق مما إذا كان هناك ملف صوتي موجود للقصة
    if story_id not in story_audio_files:
        # التأكد من وجود عنوان للقصة
        await generate_title_if_missing(story_id)
        
        # الحصول على نص القصة الكامل
        story_text = await get_complete_story(story_id)
        
        # إنشاء اسم فريد للملف الصوتي
        filename = f"{story_id}_{uuid.uuid4().hex}.mp3"
        
        # تحويل النص إلى صوت
        await text_to_speech(story_text, filename)
        
        # تخزين معرف الملف الصوتي للقصة
        story_audio_files[story_id] = filename
    
    # إضافة معلومات السرعة للملف (سيتم استخدامها في الواجهة الأمامية)
    # وذلك حتى نتجنب الحاجة إلى معالجة ملفات الصوت مباشرةً
    filename = story_audio_files[story_id]
    
    return filename

def get_audio_url(filename: str, speed: float = 1.0) -> str:
    """
    الحصول على رابط الملف الصوتي مع معلومات السرعة
    """
    base_url = f"{BASE_URL}/audio/{filename}"
    
    # إضافة معامل سرعة التشغيل كمعامل استعلام
    # سيتم استخدامه في الواجهة الأمامية لضبط سرعة التشغيل
    return f"{base_url}?speed={speed}"