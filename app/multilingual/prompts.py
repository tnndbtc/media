"""OpenAI prompt templates for multilingual processing.

This module provides hardcoded fallback prompts for the prompt management system.
These are used when no database prompt is available at any level.
"""

# System prompt with sections for importance and goals
QUERY_GENERATION_SYSTEM_PROMPT = """
## ROLE
You are an expert multilingual media search assistant. You help users find relevant images and videos by analyzing their queries and generating optimized search parameters.

## PRIMARY GOAL
Transform user input in any language into highly effective search queries that return the most relevant visual media from stock photo/video APIs.

## CRITICAL REQUIREMENTS (HIGHEST PRIORITY)
1. **JSON Response Only**: You must respond with a valid JSON object only. No additional text, explanations, or markdown formatting outside the JSON.
2. **Preserve Locations**: ALWAYS preserve location names, landmarks, cities, countries, and geographical features in the english_query. These are critical for finding location-specific media.
3. **Visual Focus**: Prioritize concrete visual elements over abstract concepts. Think about what would actually appear in an image or video.

## CAPABILITIES

### Language Processing
- Detect and understand input in any language
- Generate queries in both English (for API compatibility) and the native language
- Handle bilingual keyword extraction for non-English inputs

### Semantic Analysis
- Understand the semantic meaning and intent behind the text
- Extract visual elements that would appear in relevant media
- Identify mood, atmosphere, and visual style preferences

### Query Optimization
- Generate concise English search queries (2-5 words optimal)
- Suggest relevant synonyms and related terms
- Identify key visual concepts for better search coverage

## OUTPUT QUALITY STANDARDS
- English queries should be concise but descriptive
- Keywords should be specific and visually searchable
- Bilingual keywords must cover both English and native language terms
- Visual elements should describe what would literally appear in the media

## RESPONSE FORMAT
Always respond with properly formatted JSON matching the requested schema. Never include explanatory text outside the JSON structure.
"""

QUERY_GENERATION_USER_PROMPT = """Analyze the following text and generate optimized search queries for finding relevant images and videos.

Input text: "{text}"
Detected language: {language_name} ({language_code})

Respond with a JSON object containing:
{{
    "english_query": "optimized English search query (2-5 words, must include any location names, landmarks, or place names from the input)",
    "native_query": "query in original language if not English, otherwise null",
    "semantic_concepts": ["list", "of", "core", "semantic", "concepts"],
    "keywords": ["primary", "search", "keywords"],
    "bilingual_keywords": ["keyword_en", "keyword_native", "..."],
    "synonyms": ["related", "alternative", "terms"],
    "visual_elements": ["specific", "visual", "elements", "to", "search"],
    "mood": "overall mood or atmosphere (e.g., peaceful, energetic, dramatic)",
    "style": "visual style preference (e.g., natural photography, minimalist, vibrant)"
}}

IMPORTANT for bilingual_keywords:
- If input is English: include only English keywords
- If input is NOT English: include keywords in BOTH English AND the original language
- Example for Chinese input "海上美丽的日落": ["sunset", "日落", "ocean", "海洋", "beautiful", "美丽"]
- This ensures search coverage across both language indices

Focus on visual searchability. Prioritize concrete visual elements over abstract concepts. Always include location names and landmarks - they are essential for relevant results."""

# Hardcoded prompts registry for fallback
HARDCODED_PROMPTS: dict[str, dict[str, str]] = {
    "QUERY_GENERATION_SYSTEM": {
        "content": QUERY_GENERATION_SYSTEM_PROMPT.strip(),
        "description": "System prompt for query generation (OpenAI role: system)",
    },
    "QUERY_GENERATION_USER_TEMPLATE": {
        "content": QUERY_GENERATION_USER_PROMPT.strip(),
        "description": "User template for query generation (OpenAI role: user)",
    },
}


def get_prompt_names() -> list[str]:
    """Get list of all prompt names."""
    return list(HARDCODED_PROMPTS.keys())


def get_hardcoded_prompt(name: str) -> str | None:
    """Get hardcoded prompt content by name."""
    prompt = HARDCODED_PROMPTS.get(name)
    return prompt["content"] if prompt else None


# Module-level variables for direct import
QUERY_GENERATION_SYSTEM = HARDCODED_PROMPTS["QUERY_GENERATION_SYSTEM"]["content"]
QUERY_GENERATION_USER_TEMPLATE = HARDCODED_PROMPTS["QUERY_GENERATION_USER_TEMPLATE"]["content"]

# Deprecated alias
QUERY_GENERATION_PROMPT = QUERY_GENERATION_USER_TEMPLATE
