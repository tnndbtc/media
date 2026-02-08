"""OpenAI prompt templates for multilingual processing.

This module provides hardcoded fallback prompts for the prompt management system.
These are used when no database prompt is available at any level.
"""

# Hardcoded prompts registry for fallback
HARDCODED_PROMPTS: dict[str, dict[str, str]] = {
    "QUERY_GENERATION_SYSTEM": {
        "content": """You are a multilingual semantic search query optimizer. Your task is to analyze input text in any language and generate optimized search queries for finding relevant images and videos.

You must respond with a valid JSON object only. No additional text or explanation.

Guidelines:
1. Understand the semantic meaning and intent behind the text
2. Extract visual elements that would appear in relevant media
3. Generate an optimized English search query (as stock media APIs work best with English)
4. If the input is not in English, also provide a native language query
5. Identify key visual concepts, mood, and style
6. Suggest relevant synonyms and related terms
7. IMPORTANT: Always preserve location names, landmarks, cities, countries, and geographical features in the english_query. These are critical for finding location-specific media.""",
        "description": "System prompt for query generation agent",
    },
    "QUERY_GENERATION_PROMPT": {
        "content": """Analyze the following text and generate optimized search queries for finding relevant images and videos.

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

Focus on visual searchability. Prioritize concrete visual elements over abstract concepts. Always include location names and landmarks - they are essential for relevant results.""",
        "description": "User prompt template for query generation",
    },
    "SEMANTIC_ANALYSIS_PROMPT": {
        "content": """Analyze this text for semantic media search optimization.

Text: "{text}"

Provide a detailed analysis in JSON format:
{{
    "primary_subject": "main subject or topic",
    "visual_description": "how this would look visually",
    "color_palette": ["suggested", "colors"],
    "composition_hints": ["framing", "suggestions"],
    "related_concepts": ["broader", "related", "ideas"],
    "search_strategies": [
        {{"query": "search term 1", "rationale": "why this query"}},
        {{"query": "search term 2", "rationale": "why this query"}}
    ]
}}""",
        "description": "Prompt for semantic analysis of search queries",
    },
    "LANGUAGE_DETECTION_PROMPT": {
        "content": """Identify the language of this text and provide context.

Text: "{text}"

Respond with JSON:
{{
    "language_code": "ISO 639-1 code",
    "language_name": "Full language name",
    "confidence": 0.95,
    "script": "writing system used",
    "region_hint": "regional variant if detectable"
}}""",
        "description": "Prompt for language detection",
    },
    "TRANSLATION_PROMPT": {
        "content": """Translate this text to English, preserving the visual and emotional meaning for media search purposes.

Original text: "{text}"
Source language: {source_language}

Provide JSON response:
{{
    "translation": "English translation",
    "visual_meaning": "what this would look like visually",
    "cultural_context": "any relevant cultural context",
    "search_terms": ["suggested", "english", "search", "terms"]
}}""",
        "description": "Prompt for translation with visual context",
    },
    "RANKING_RELEVANCE_PROMPT": {
        "content": """Evaluate how well these media items match the search intent.

Original query: "{query}"
Search intent: {intent}

Media items to evaluate:
{items}

For each item, provide a relevance score (0.0-1.0) and brief rationale.
Respond with JSON array:
[
    {{"id": "item_id", "relevance_score": 0.85, "rationale": "why relevant"}}
]""",
        "description": "Prompt for ranking media relevance",
    },
}


def get_prompt_names() -> list[str]:
    """Get list of all prompt names.

    Returns:
        List of prompt names
    """
    return list(HARDCODED_PROMPTS.keys())


def get_hardcoded_prompt(name: str) -> str | None:
    """Get hardcoded prompt content by name.

    Args:
        name: Prompt name

    Returns:
        Prompt content or None if not found
    """
    prompt = HARDCODED_PROMPTS.get(name)
    return prompt["content"] if prompt else None


# Backward compatibility: expose prompts as module-level variables
QUERY_GENERATION_SYSTEM = HARDCODED_PROMPTS["QUERY_GENERATION_SYSTEM"]["content"]
QUERY_GENERATION_PROMPT = HARDCODED_PROMPTS["QUERY_GENERATION_PROMPT"]["content"]
SEMANTIC_ANALYSIS_PROMPT = HARDCODED_PROMPTS["SEMANTIC_ANALYSIS_PROMPT"]["content"]
LANGUAGE_DETECTION_PROMPT = HARDCODED_PROMPTS["LANGUAGE_DETECTION_PROMPT"]["content"]
TRANSLATION_PROMPT = HARDCODED_PROMPTS["TRANSLATION_PROMPT"]["content"]
RANKING_RELEVANCE_PROMPT = HARDCODED_PROMPTS["RANKING_RELEVANCE_PROMPT"]["content"]
