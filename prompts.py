from typing import List, Dict, Any
from models import StoryLength, StoryType, Character, StoryConfig


def get_system_prompt() -> str:
    """
    الحصول على برومبت النظام الأساسي الذي يحدد سلوك نموذج الذكاء الاصطناعي
    """
    return """
    You are a professional and creative Arabic story writer. Your task is to write original, engaging, and cohesive Arabic stories.
    
    Adhere to the following standards in all the stories you write:

    1. Use correct and understandable classical Arabic language, free from grammatical and spelling errors.
    2. Build a coherent and logical story that follows good dramatic structure principles (beginning, rising action, climax, resolution).
    3. Adhere to Arabic and Islamic values and ethics in the story content.
    4. Avoid inappropriate content or anything that violates public taste or religious values.
    5. Provide detailed sensory descriptions of characters, places, and events to make the story vivid and engaging.
    6. Make dialogue realistic and natural, appropriate to the story's characters and environment.
    7. Maintain consistency in character traits and behaviors throughout the story.
    8. Include positive values and useful lessons in an indirect way.
    9. Use diverse narrative techniques: description, dialogue, narration, internal monologue.
    10. Create a clear conflict that drives the story events and maintains reader interest.

    Each time you are asked to write a new paragraph of the story, you must:
    - Write a coherent and engaging narrative paragraph of 4-6 lines in Arabic.
    - Provide 3 distinctive and interesting options to develop the story's path.
    
    Important rules for options:
    1. Make options very practical and short (3-5 words only) in Arabic.
    2. ALWAYS start each option with the character's name followed by the action verb.
    3. Use clear format: "[Character name] + verb", for example: "أحمد يتصل بالشرطة" (Ahmed calls the police), "سارة تهرب من المكان" (Sarah escapes from the place).
    4. Make it absolutely clear WHO is performing the action in each option.
    5. Don't explain what will happen after the choice, just mention the direct action.
    6. Ensure each option will lead to a completely different path in the story.
    7. Make options logical and appropriate to the current situation in the story.
    
    Result of user choice:
    1. Do not summarize the user's chosen option at the beginning of the next paragraph.
    2. Start directly with the reactions and consequences resulting from the user's choice.
    3. Present surprising and unexpected developments resulting from the choice.
    4. Maintain story consistency despite the change in path.
    
    When the story is complete, choose an engaging and deep title that reflects the essence and content of the story.
    """


def format_characters_info(characters: List[Character]) -> str:
    """
    تنسيق معلومات الشخصيات لتضمينها في البرومبت
    """
    if not characters:
        return "لا توجد شخصيات محددة، يمكنك إنشاء شخصيات مناسبة للقصة."
    
    characters_info = "معلومات الشخصيات:\n"
    for i, character in enumerate(characters, 1):
        gender_text = "ذكر" if character.gender.value == "ذكر" else "أنثى"
        characters_info += f"{i}. الشخصية: {character.name}، الجنس: {gender_text}، الوصف: {character.description}\n"
    
    return characters_info


def get_story_length_instructions(length: StoryLength) -> Dict[str, Any]:
    """
    الحصول على تعليمات طول القصة وعدد الفقرات
    """
    length_mapping = {
        StoryLength.SHORT: {"paragraphs": 3, "description": "قصة قصيرة تتكون من 3 فقرات"},
        StoryLength.MEDIUM: {"paragraphs": 5, "description": "قصة متوسطة الطول تتكون من 5 فقرات"},
        StoryLength.LONG: {"paragraphs": 7, "description": "قصة طويلة تتكون من 7 فقرات"}
    }
    
    return length_mapping.get(length, length_mapping[StoryLength.MEDIUM])


def get_story_type_description(primary_type: StoryType, secondary_type: StoryType) -> str:
    """
    الحصول على وصف نوع القصة
    """
    if secondary_type == StoryType.NONE:
        return f"قصة من نوع {primary_type.value}"
    else:
        return f"قصة تجمع بين نوعي {primary_type.value} و{secondary_type.value}"


def create_story_init_prompt(config: StoryConfig) -> str:
    """
    إنشاء البرومبت الأولي لبدء القصة
    """
    length_info = get_story_length_instructions(config.length)
    story_type = get_story_type_description(config.primary_type, config.secondary_type)
    characters_info = format_characters_info(config.characters)
    
    prompt = f"""
    Please write {length_info['description']} of {story_type}.
    
    {characters_info}
    
    Required from you:
    1. Write the first paragraph of the story (4-6 lines) in Arabic.
    2. Start the story with a strong and engaging beginning that captivates the reader from the first line.
    3. Present the characters and setting (place and time) clearly and interestingly.
    4. Establish a conflict, problem, or situation that drives the story events.
    5. Present 3 short, exciting, and logical options for actions the protagonist can take.
    6. Make the options very short (3-5 words only) and practical and direct.
    7. ALWAYS include the character's name in each option before the action verb.
    8. Format: "[Character name] + verb", like: "أحمد يتصل بالشرطة", "سارة تهرب من المكان".
    
    Present the first paragraph and options in the following format:
    
    الفقرة:
    [Write the first paragraph of the story here in Arabic]
    
    الخيارات:
    1. [Character name + action verb in Arabic, 3-5 words total]
    2. [Character name + different action verb in Arabic, 3-5 words total]
    3. [Character name + another different action verb in Arabic, 3-5 words total]
    """
    
    return prompt


def create_continuation_prompt(story_context: str, choice_id: int, choice_text: str, current_paragraph: int, max_paragraphs: int) -> str:
    """
    إنشاء برومبت لاستكمال القصة بناءً على اختيار المستخدم
    """
    is_final = current_paragraph >= max_paragraphs - 1
    
    prompt = f"""
    Story context so far:
    {story_context}
    
    The user chose path number {choice_id}: {choice_text}
    
    Required from you:
    1. Continue writing the story with a new paragraph (4-6 lines) in Arabic that directly follows the choice made by the user.
    2. Do not summarize the choice that the user made; instead, start directly with the events that result from this choice.
    3. Add unexpected and exciting developments to engage the reader.
    4. Maintain consistency in the story's characters and world.
    """
    
    if is_final:
        prompt += """
    5. This is the final paragraph of the story, so end the story in a logical and satisfying way that closes all open paths.
    6. Suggest an appropriate and deep title for the complete story.
    
    Present the final paragraph and title in the following format:
    
    الفقرة:
    [Write the final paragraph of the story here in Arabic]
    
    العنوان:
    [Write the suggested title for the story here in Arabic]
    """
    else:
        prompt += """
    5. Present 3 short, logical, and practical options for continuing the story.
    6. Make the options very short (3-5 words only) in Arabic.
    7. ALWAYS include the character's name in each option before the action verb.
    8. Format: "[Character name] + verb", like: "أحمد يتصل بالشرطة", "سارة تهرب من المكان".
    9. Make it absolutely clear WHO is performing the action in each option.
    10. Ensure each option will lead to a completely different path in the story.
    
    Present the next paragraph and options in the following format:
    
    الفقرة:
    [Write the next paragraph of the story here in Arabic]
    
    الخيارات:
    1. [Character name + action verb in Arabic, 3-5 words total]
    2. [Character name + different action verb in Arabic, 3-5 words total]
    3. [Character name + another different action verb in Arabic, 3-5 words total]
    """
    
    return prompt


def create_title_prompt(complete_story: str) -> str:
    """
    إنشاء برومبت لتوليد عنوان مناسب للقصة المكتملة
    """
    return f"""
    Here is a complete story:
    
    {complete_story}
    
    Suggest an appropriate and engaging title for this story that reflects its essence and content.
    Provide only the title without any additional explanation and without any story Characters names in Arabic.
    """