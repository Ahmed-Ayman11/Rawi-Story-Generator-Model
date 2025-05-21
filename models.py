"""
راوي (Rawi) - Arabic AI Storytelling Platform
Data models for API requests and responses
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ======== Enum Types ========

class StoryLength(str, Enum):
    """Story length options"""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class StoryType(str, Enum):
    """Story genre options in Arabic"""
    ROMANCE = "رومانسي"
    HORROR = "رعب"
    COMEDY = "كوميدي"
    ACTION = "أكشن"
    ADVENTURE = "مغامرة"
    DRAMA = "دراما"
    FANTASY = "خيال"
    HISTORICAL = "تاريخي"
    MYSTERY = "غموض"
    NONE = "لا"


class CharacterGender(str, Enum):
    """Character gender options in Arabic"""
    MALE = "ذكر"
    FEMALE = "أنثى"


# ======== Request Models ========

class Character(BaseModel):
    """Character information for story generation"""
    name: str = Field(..., description="اسم الشخصية")
    gender: CharacterGender = Field(..., description="جنس الشخصية")
    description: str = Field(..., description="وصف الشخصية")


class StoryConfig(BaseModel):
    """Configuration for initial story generation"""
    length: StoryLength = Field(..., description="طول القصة")
    primary_type: StoryType = Field(..., description="النوع الأساسي للقصة")
    secondary_type: StoryType = Field(default=StoryType.NONE, description="النوع الثانوي للقصة")
    characters: List[Character] = Field(default=[], description="الشخصيات في القصة")


class ChoiceRequest(BaseModel):
    """Request to continue a story with a choice or custom text"""
    story_id: str = Field(..., description="معرف القصة")
    choice_id: Optional[int] = Field(None, description="معرف الاختيار الذي تم اختياره")
    custom_text: Optional[str] = Field(None, description="النص المخصص الذي أدخله المستخدم")


class TTSRequest(BaseModel):
    """Request to generate text-to-speech for a story"""
    story_id: str = Field(..., description="معرف القصة")
    speed: float = Field(1.0, description="سرعة الصوت (0.5 للبطيء، 1.0 للعادي، 2.0 للسريع)", ge=0.5, le=2.0)


class EditRequest(BaseModel):
    """Request to edit a story based on user instructions"""
    story_id: str = Field(..., description="معرف القصة")
    edit_instructions: str = Field(..., description="تعليمات لتعديل القصة")


# ======== Response Models ========

class StoryChoice(BaseModel):
    """A choice option presented to the user"""
    id: int = Field(..., description="معرف الاختيار")
    text: str = Field(..., description="نص الاختيار")


class StoryParagraph(BaseModel):
    """A paragraph of story content with optional choices"""
    content: str = Field(..., description="محتوى الفقرة")
    choices: Optional[List[StoryChoice]] = Field(default=None, description="الاختيارات المتاحة بعد هذه الفقرة")


class StoryResponse(BaseModel):
    """Response containing story content and metadata"""
    story_id: str = Field(..., description="معرف القصة")
    paragraph: StoryParagraph = Field(..., description="فقرة من القصة")
    is_complete: bool = Field(default=False, description="هل القصة اكتملت؟")
    title: Optional[str] = Field(default=None, description="عنوان القصة (يتم إضافته عند اكتمال القصة)")


class TTSResponse(BaseModel):
    """Response containing URL to audio file"""
    audio_url: str = Field(..., description="رابط ملف الصوت")


class EditResponse(BaseModel):
    """Response containing edited story content"""
    success: bool = Field(default=True, description="نجاح عملية التعديل")
    paragraphs: List[str] = Field(..., description="فقرات القصة المعدلة")
    title: Optional[str] = Field(default=None, description="عنوان القصة المعدل (اختياري)")