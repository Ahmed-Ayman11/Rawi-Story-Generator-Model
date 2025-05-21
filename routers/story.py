import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path

from models import StoryConfig, StoryResponse, ChoiceRequest, TTSRequest, TTSResponse, EditRequest, EditResponse
from ai_service import initialize_story, continue_story, continue_story_with_text, get_complete_story, edit_story
from tts_service import generate_audio_for_story, get_audio_url

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# الحصول على مسار تخزين ملفات الصوت
AUDIO_STORAGE_PATH = os.path.abspath(os.getenv("AUDIO_STORAGE_PATH", "./audio_files"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

logger.info(f"Audio storage path: {AUDIO_STORAGE_PATH}")
logger.info(f"Base URL: {BASE_URL}")


@router.post("/initialize", response_model=StoryResponse)
async def create_story(config: StoryConfig):
    """
    بدء قصة جديدة بناءً على التكوين المقدم
    """
    try:
        # Log the incoming request data
        print(f"Request data: {config.dict()}")
        
        response = await initialize_story(config)
        return response
    except Exception as e:
        # Log the error details
        print(f"Error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء إنشاء القصة: {str(e)}")


@router.post("/continue", response_model=StoryResponse)
async def continue_story_route(request: ChoiceRequest):
    """
    متابعة القصة بناءً على اختيار المستخدم أو إدخال نص مخصص
    """
    try:
        # Log the request for debugging
        logger.info(f"Continuing story with: {request.dict()}")
        
        if request.choice_id is not None:
            # استخدام الاختيار المحدد
            response = await continue_story(request.story_id, request.choice_id)
        elif request.custom_text is not None:
            # استخدام النص المخصص
            response = await continue_story_with_text(request.story_id, request.custom_text)
        else:
            # لا يوجد اختيار أو نص مخصص
            raise ValueError("يجب تحديد اختيار أو إدخال نص مخصص")
            
        return response
    except ValueError as e:
        logger.error(f"ValueError in continue_story_route: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in continue_story_route: {str(e)}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء متابعة القصة: {str(e)}")


@router.get("/story/{story_id}", response_model=str)
async def get_story(story_id: str):
    """
    الحصول على نص القصة الكامل
    """
    try:
        complete_story = await get_complete_story(story_id)
        return complete_story
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء استرجاع القصة: {str(e)}")


@router.post("/tts", response_model=TTSResponse)
async def generate_tts(request: TTSRequest):
    """
    توليد ملف صوتي للقصة بسرعة محددة
    """
    try:
        logger.info(f"Generating TTS for story ID: {request.story_id} with speed: {request.speed}")
        
        # توليد أو استرجاع الملف الصوتي
        audio_filename = await generate_audio_for_story(request.story_id)
        logger.info(f"Audio filename: {audio_filename}")
        
        # إنشاء URL للملف الصوتي مع تمرير معلومات السرعة
        audio_url = get_audio_url(audio_filename, request.speed)
        logger.info(f"Audio URL: {audio_url}")
        
        return TTSResponse(audio_url=audio_url)
    except ValueError as e:
        logger.error(f"ValueError in generate_tts: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in generate_tts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء توليد الصوت: {str(e)}")


@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """
    استرجاع ملف صوتي محدد
    """
    try:
        file_path = os.path.join(AUDIO_STORAGE_PATH, filename)
        logger.info(f"Attempting to serve audio file: {file_path}")
        
        if not Path(file_path).exists():
            logger.error(f"Audio file not found: {file_path}")
            raise HTTPException(status_code=404, detail="الملف الصوتي غير موجود")
        
        logger.info(f"Serving audio file: {file_path}")
        return FileResponse(
            path=file_path,
            media_type="audio/mpeg",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء استرجاع الملف الصوتي: {str(e)}")


@router.post("/edit", response_model=EditResponse)
async def edit_story_endpoint(request: EditRequest):
    """
    تعديل القصة بناءً على تعليمات المستخدم
    """
    try:
        logger.info(f"Editing story with ID: {request.story_id}")
        logger.info(f"Edit instructions: {request.edit_instructions}")
        
        # استدعاء خدمة التعديل
        edit_result = await edit_story(request.story_id, request.edit_instructions)
        
        return EditResponse(
            success=True,
            paragraphs=edit_result["paragraphs"],
            title=edit_result["title"]
        )
    except ValueError as e:
        logger.error(f"ValueError in edit_story_endpoint: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in edit_story_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء تعديل القصة: {str(e)}")