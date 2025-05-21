import os
import json
import re
import time
import asyncio
from typing import Dict, List, Tuple, Optional
import httpx
from dotenv import load_dotenv

from models import StoryConfig, StoryParagraph, StoryChoice, StoryResponse
from prompts import (
    get_system_prompt, 
    create_story_init_prompt, 
    create_continuation_prompt,
    create_title_prompt,
    get_story_length_instructions
)

# تحميل المتغيرات البيئية
load_dotenv()

# الحصول على مفتاح API من المتغيرات البيئية
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# تخزين سياق القصص
# في نظام حقيقي، يجب استخدام قاعدة بيانات بدلاً من التخزين في الذاكرة
stories_context = {}
stories_metadata = {}


async def generate_response(messages: List[Dict], retries=3, backoff_factor=1.5) -> str:
    """
    استدعاء DeepSeek API وتوليد استجابة بناءً على سلسلة الرسائل مع محاولة إعادة المحاولة في حالة الفشل
    
    Args:
        messages: قائمة برسائل المحادثة
        retries: عدد محاولات إعادة المحاولة في حالة فشل الاتصال (افتراضي: 3)
        backoff_factor: معامل التأخير للمحاولات المتتالية (افتراضي: 1.5)
        
    Returns:
        str: محتوى الاستجابة من API
        
    Raises:
        Exception: في حالة فشل جميع المحاولات
    """
    if not DEEPSEEK_API_KEY:
        raise Exception("مفتاح API غير متوفر. يرجى التحقق من إعداد المتغيرات البيئية.")
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    payload = {
        "model": "deepseek-chat",  # استبدل باسم النموذج المناسب من DeepSeek API
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    last_exception = None
    
    # محاولات إعادة الاتصال في حالة فشل API
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 429:  # Rate Limit
                    # انتظار فترة قبل المحاولة مرة أخرى
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"تجاوز حد معدل الطلبات، انتظار {wait_time} ثانية قبل المحاولة مرة أخرى.")
                    await asyncio.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    error_msg = f"فشل طلب DeepSeek API: {response.status_code} - {response.text}"
                    print(error_msg)
                    last_exception = Exception(error_msg)
                    
                    # انتظار فترة قبل المحاولة مرة أخرى
                    wait_time = backoff_factor * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
                
                result = response.json()
                if "choices" not in result or not result["choices"]:
                    raise Exception("تنسيق استجابة DeepSeek API غير صالح")
                    
                return result["choices"][0]["message"]["content"]
                
        except httpx.HTTPError as e:
            error_msg = f"خطأ في اتصال HTTP: {str(e)}"
            print(error_msg)
            last_exception = Exception(error_msg)
            
            # انتظار فترة قبل المحاولة مرة أخرى
            wait_time = backoff_factor * (2 ** attempt)
            await asyncio.sleep(wait_time)
            continue
            
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {str(e)}"
            print(error_msg)
            last_exception = Exception(error_msg)
            
            # انتظار فترة قبل المحاولة مرة أخرى
            wait_time = backoff_factor * (2 ** attempt)
            await asyncio.sleep(wait_time)
            continue
    
    # إذا وصلنا إلى هنا، فقد فشلت جميع المحاولات
    raise last_exception or Exception("فشل الاتصال بـ DeepSeek API بعد عدة محاولات")


def parse_paragraph_and_choices(response_text: str) -> Tuple[str, Optional[List[StoryChoice]]]:
    """
    تحليل استجابة النموذج واستخراج الفقرة والخيارات
    """
    # محاولة استخراج الفقرة
    paragraph_match = re.search(r"الفقرة:(.*?)(?:الخيارات:|العنوان:|$)", response_text, re.DOTALL)
    paragraph = paragraph_match.group(1).strip() if paragraph_match else response_text.strip()
    
    # محاولة استخراج الخيارات
    choices = None
    choices_match = re.search(r"الخيارات:(.*?)(?:$)", response_text, re.DOTALL)
    
    if choices_match:
        choices_text = choices_match.group(1).strip()
        choices = []
        
        # استخراج الخيارات المرقمة
        for i, choice_match in enumerate(re.findall(r"\d+\.\s*(.*?)(?=\d+\.|$)", choices_text, re.DOTALL), 1):
            choice_text = choice_match.strip()
            if choice_text:
                choices.append(StoryChoice(id=i, text=choice_text))
        
        # إذا لم يتم العثور على خيارات بالطريقة السابقة، نحاول طريقة أخرى
        if not choices:
            lines = choices_text.split("\n")
            for i, line in enumerate([l for l in lines if l.strip()], 1):
                if i <= 3:  # نقتصر على 3 خيارات
                    # تجاهل الترقيم إذا كان موجوداً
                    choice_text = re.sub(r"^\d+\.\s*", "", line).strip()
                    choices.append(StoryChoice(id=i, text=choice_text))
    
    # استخراج العنوان إذا كان موجوداً
    title = None
    title_match = re.search(r"العنوان:(.*?)(?:$)", response_text, re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
    
    return paragraph, choices, title


async def initialize_story(config: StoryConfig) -> StoryResponse:
    """
    بدء قصة جديدة باستخدام DeepSeek API
    """
    import uuid
    story_id = str(uuid.uuid4())
    
    # إنشاء البرومبت الأولي
    system_prompt = get_system_prompt()
    user_prompt = create_story_init_prompt(config)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # استدعاء DeepSeek API
    response_text = await generate_response(messages)
    
    # تحليل الاستجابة
    paragraph_text, choices, _ = parse_paragraph_and_choices(response_text)
    
    # إنشاء فقرة القصة
    paragraph = StoryParagraph(
        content=paragraph_text,
        choices=choices
    )
    
    # حفظ سياق القصة
    stories_context[story_id] = {
        "paragraphs": [paragraph_text],
        "current_paragraph": 1
    }
    
    # حفظ معلومات القصة
    length_info = get_story_length_instructions(config.length)
    stories_metadata[story_id] = {
        "config": config.dict(),
        "max_paragraphs": length_info["paragraphs"],
        "messages": messages + [{"role": "assistant", "content": response_text}],
        "title": None
    }
    
    # إنشاء استجابة القصة
    story_response = StoryResponse(
        story_id=story_id,
        paragraph=paragraph,
        is_complete=False
    )
    
    return story_response


async def continue_story(story_id: str, choice_id: int) -> StoryResponse:
    """
    متابعة القصة بناءً على اختيار المستخدم
    """
    if story_id not in stories_context or story_id not in stories_metadata:
        raise ValueError("معرف القصة غير صالح")
    
    context = stories_context[story_id]
    metadata = stories_metadata[story_id]
    
    # الحصول على سياق القصة والاختيار
    paragraphs = context["paragraphs"]
    current_paragraph = context["current_paragraph"]
    max_paragraphs = metadata["max_paragraphs"]
    
    # الحصول على الرسائل السابقة
    messages = metadata["messages"]
    
    # الحصول على نص الاختيار
    last_message = messages[-1]["content"]
    _, choices, _ = parse_paragraph_and_choices(last_message)
    
    if not choices or choice_id < 1 or choice_id > len(choices):
        raise ValueError("معرف الاختيار غير صالح")
    
    choice_text = next((c.text for c in choices if c.id == choice_id), "")
    
    # إنشاء برومبت المتابعة
    story_context_text = "\n".join(paragraphs)
    continuation_prompt = create_continuation_prompt(
        story_context_text, 
        choice_id, 
        choice_text, 
        current_paragraph, 
        max_paragraphs
    )
    
    # إضافة رسالة المستخدم
    messages.append({"role": "user", "content": continuation_prompt})
    
    # استدعاء DeepSeek API
    response_text = await generate_response(messages)
    
    # تحليل الاستجابة
    paragraph_text, choices, title = parse_paragraph_and_choices(response_text)
    
    # تحديث سياق القصة
    paragraphs.append(paragraph_text)
    context["current_paragraph"] += 1
    context["paragraphs"] = paragraphs
    
    # تحديد ما إذا كانت القصة مكتملة
    is_complete = current_paragraph >= max_paragraphs - 1
    
    # إذا كانت القصة مكتملة، احفظ العنوان
    if is_complete and title:
        metadata["title"] = title
    
    # تحديث الرسائل
    messages.append({"role": "assistant", "content": response_text})
    metadata["messages"] = messages
    
    # إنشاء فقرة القصة
    paragraph = StoryParagraph(
        content=paragraph_text,
        choices=None if is_complete else choices
    )
    
    # إنشاء استجابة القصة
    story_response = StoryResponse(
        story_id=story_id,
        paragraph=paragraph,
        is_complete=is_complete,
        title=metadata["title"] if is_complete else None
    )
    
    return story_response


async def continue_story_with_text(story_id: str, custom_text: str) -> StoryResponse:
    """
    متابعة القصة بناءً على النص المخصص الذي أدخله المستخدم
    """
    print(f"continue_story_with_text called with story_id={story_id}, custom_text={custom_text}")
    
    if story_id not in stories_context or story_id not in stories_metadata:
        print(f"Story ID {story_id} not found in context or metadata")
        raise ValueError("معرف القصة غير صالح")
    
    context = stories_context[story_id]
    metadata = stories_metadata[story_id]
    
    # الحصول على سياق القصة
    paragraphs = context["paragraphs"]
    current_paragraph = context["current_paragraph"]
    max_paragraphs = metadata["max_paragraphs"]
    
    print(f"Story context: current_paragraph={current_paragraph}, max_paragraphs={max_paragraphs}")
    
    # الحصول على الرسائل السابقة
    messages = metadata["messages"]
    
    # إنشاء برومبت المتابعة بالنص المخصص
    story_context_text = "\n".join(paragraphs)
    
    # Create a prompt for continuing with custom text
    custom_prompt = f"""
لقد وصلنا إلى هذه النقطة في القصة:

{story_context_text}

المستخدم اختار أن يكتب رداً مخصصاً بدلاً من اختيار أحد الخيارات المقدمة. الرد المخصص للمستخدم هو:

"{custom_text}"

بناءً على هذا المدخل من المستخدم، استمر في القصة واكتب فقرة جديدة تأخذ بعين الاعتبار ما كتبه المستخدم.
ثم قدم 3 خيارات جديدة للمستخدم ليختار منها للاستمرار في القصة.

تذكر أن القصة الآن في:
- الفقرة رقم: {current_paragraph} من {max_paragraphs}
- إذا كانت هذه الفقرة الأخيرة أو قبل الأخيرة، قم بختم القصة بشكل مناسب.

يجب أن يكون تنسيق ردك كما يلي:

الفقرة: [نص الفقرة الجديدة من القصة]

الخيارات:
1. [الخيار الأول]
2. [الخيار الثاني]
3. [الخيار الثالث]

إذا كانت هذه الفقرة الأخيرة، أضف عنواناً للقصة:

العنوان: [عنوان مناسب للقصة كاملة]
"""
    
    print(f"Custom prompt created, length: {len(custom_prompt)}")
    
    # إضافة رسالة المستخدم
    messages.append({"role": "user", "content": custom_prompt})
    
    # استدعاء DeepSeek API
    print("Calling DeepSeek API...")
    response_text = await generate_response(messages)
    print(f"DeepSeek API response received, length: {len(response_text)}")
    
    # تحليل الاستجابة
    paragraph_text, choices, title = parse_paragraph_and_choices(response_text)
    print(f"Parsed response: paragraph length={len(paragraph_text)}, choices={choices is not None}, title={title is not None}")
    
    # تحديث سياق القصة
    paragraphs.append(paragraph_text)
    context["current_paragraph"] += 1
    context["paragraphs"] = paragraphs
    
    # تحديد ما إذا كانت القصة مكتملة
    is_complete = current_paragraph >= max_paragraphs - 1
    print(f"Is story complete: {is_complete}")
    
    # إذا كانت القصة مكتملة، احفظ العنوان
    if is_complete and title:
        metadata["title"] = title
    
    # تحديث الرسائل
    messages.append({"role": "assistant", "content": response_text})
    metadata["messages"] = messages
    
    # إنشاء فقرة القصة
    paragraph = StoryParagraph(
        content=paragraph_text,
        choices=None if is_complete else choices
    )
    
    # إنشاء استجابة القصة
    story_response = StoryResponse(
        story_id=story_id,
        paragraph=paragraph,
        is_complete=is_complete,
        title=metadata["title"] if is_complete else None
    )
    
    print(f"Story response created successfully")
    return story_response


async def get_complete_story(story_id: str) -> str:
    """
    الحصول على النص الكامل للقصة
    """
    if story_id not in stories_context:
        raise ValueError("معرف القصة غير صالح")
    
    context = stories_context[story_id]
    metadata = stories_metadata.get(story_id, {})
    
    story_text = "\n\n".join(context["paragraphs"])
    
    if metadata.get("title"):
        # إضافة العنوان بصيغة صديقة لخدمة تحويل النص إلى كلام
        story_text = f"قصة بعنوان {metadata['title']}.\n\n{story_text}"
    
    return story_text


async def generate_title_if_missing(story_id: str) -> str:
    """
    توليد عنوان للقصة إذا لم يكن موجوداً
    """
    if story_id not in stories_metadata:
        raise ValueError("معرف القصة غير صالح")
        
    metadata = stories_metadata[story_id]
    
    # إذا كان العنوان موجوداً بالفعل، أعده
    if metadata.get("title"):
        return metadata["title"]
    
    # توليد العنوان
    complete_story = await get_complete_story(story_id)
    
    system_prompt = get_system_prompt()
    title_prompt = create_title_prompt(complete_story)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": title_prompt}
    ]
    
    title = await generate_response(messages)
    
    # تنظيف العنوان
    title = title.strip().replace("العنوان:", "").strip()
    
    # حفظ العنوان
    metadata["title"] = title
    
    return title

async def edit_story(story_id: str, edit_instructions: str) -> dict:
    """
    تعديل القصة بناءً على تعليمات المستخدم
    """
    if story_id not in stories_context or story_id not in stories_metadata:
        raise ValueError("معرف القصة غير صالح")
    
    # الحصول على نص القصة الكامل
    paragraphs = stories_context[story_id]["paragraphs"]
    complete_story = "\n".join(paragraphs)
    
    # إنشاء برومبت للتعديل
    system_prompt = """أنت مساعد ذكي متخصص في تحرير وتعديل القصص العربية. مهمتك هي تعديل القصة بناءً على تعليمات المستخدم مع الحفاظ على الأسلوب والنبرة الأصلية. 
قم بإرجاع القصة المعدلة بالكامل وليس فقط الأجزاء المعدلة. تأكد من تقسيم القصة إلى فقرات واضحة كما في النص الأصلي.
إذا تطلبت التعليمات تغيير العنوان، قم بإضافة سطر "العنوان الجديد: <العنوان المعدل>" في بداية استجابتك."""
    
    user_prompt = f"""فيما يلي قصة كاملة:
    
{complete_story}

تعليمات التعديل:
{edit_instructions}

قم بتعديل القصة وفقًا للتعليمات المذكورة أعلاه وأرجع القصة المعدلة بالكامل مقسمة إلى فقرات.
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # استدعاء DeepSeek API
    response_text = await generate_response(messages)
    
    # تحليل النص واستخراج العنوان الجديد إذا وجد
    new_title = None
    title_match = re.search(r"العنوان الجديد:\s*(.*?)(?:\n|$)", response_text, re.IGNORECASE)
    if title_match:
        new_title = title_match.group(1).strip()
        response_text = re.sub(r"العنوان الجديد:\s*.*?(?:\n|$)", "", response_text, flags=re.IGNORECASE)
    
    # تقسيم النص المعدل إلى فقرات
    edited_paragraphs = [p.strip() for p in response_text.split("\n\n") if p.strip()]
    
    # تحديث القصة في التخزين
    stories_context[story_id]["paragraphs"] = edited_paragraphs
    
    # تحديث العنوان إذا كان هناك عنوان جديد
    if new_title:
        stories_metadata[story_id]["title"] = new_title
    
    # إرجاع البيانات المعدلة
    return {
        "paragraphs": edited_paragraphs,
        "title": new_title or stories_metadata[story_id].get("title")
    }