"""
Hardcoded suggestions for the Intake Agent to provide quick-reply options.
These are organized by question type for easy matching.
"""

# Common visa types with Japanese names
VISA_TYPES = [
    "Student (留学)",
    "Work (就労)",
    "Spouse (配偶者)",
    "Dependent (家族滞在)",
    "Permanent Resident (永住者)",
    "Tourist (短期滞在)",
    "Business Manager (経営・管理)",
    "Highly Skilled Professional (高度専門職)",
    "Engineer/Specialist (技術・人文知識・国際業務)",
    "Other",
]

# Major cities in Japan
MAJOR_CITIES = [
    "Tokyo (東京)",
    "Yokohama (横浜)",
    "Osaka (大阪)",
    "Kyoto (京都)",
    "Nagoya (名古屋)",
    "Sapporo (札幌)",
    "Fukuoka (福岡)",
    "Kobe (神戸)",
    "Other",
]

# Common timeline/urgency options
TIMELINES = [
    "Urgent (within 1 week)",
    "Soon (within 1 month)",
    "Normal (1-3 months)",
    "Long-term (3+ months)",
    "No specific deadline",
]

# Yes/No for binary questions
YES_NO = ["Yes", "No", "Not sure"]

# Common document types
DOCUMENT_TYPES = [
    "Residence Card (在留カード)",
    "Passport",
    "Certificate of Eligibility (在留資格認定証明書)",
    "Work permit",
    "Birth certificate",
    "Marriage certificate",
    "Other",
]

# Language preferences
LANGUAGES = ["English", "Japanese", "Both", "Other"]


def get_suggestions_for_question(question: str, context: dict = None) -> list:
    """
    Analyze the question and return appropriate quick-reply suggestions.

    Args:
        question: The question being asked
        context: Additional context from the intake session

    Returns:
        List of suggested quick-reply options
    """
    question_lower = question.lower()

    # Visa type questions
    if any(
        keyword in question_lower
        for keyword in [
            "visa type",
            "what type of visa",
            "visa status",
            "status of residence",
        ]
    ):
        return VISA_TYPES

    # Location questions
    if any(
        keyword in question_lower
        for keyword in [
            "city",
            "location",
            "where",
            "prefecture",
            "municipality",
            "live",
            "residing",
        ]
    ):
        return MAJOR_CITIES

    # Timeline/urgency questions
    if any(
        keyword in question_lower
        for keyword in [
            "when",
            "timeline",
            "urgency",
            "deadline",
            "how soon",
            "by when",
        ]
    ):
        return TIMELINES

    # Binary questions (yes/no)
    if any(
        keyword in question_lower
        for keyword in ["have you", "did you", "do you", "are you", "is it", "can you"]
    ):
        return YES_NO

    # Document questions
    if any(
        keyword in question_lower
        for keyword in ["document", "paper", "certificate", "proof"]
    ):
        return DOCUMENT_TYPES

    # Language questions
    if any(keyword in question_lower for keyword in ["language", "speak", "prefer"]):
        return LANGUAGES

    # Default: no suggestions (free-form answer)
    return []


def format_suggestion_for_display(suggestion: str) -> str:
    """
    Format a suggestion for display in the UI.
    Can be used to adjust formatting if needed.
    """
    return suggestion


# Question patterns that should trigger specific suggestion sets
# This can be expanded for more sophisticated matching
QUESTION_PATTERNS = {
    "visa_type": {
        "keywords": [
            "visa type",
            "what type of visa",
            "visa status",
            "status of residence",
            "what visa",
        ],
        "suggestions": VISA_TYPES,
    },
    "location": {
        "keywords": [
            "city",
            "location",
            "where",
            "prefecture",
            "live",
            "residing",
            "which city",
        ],
        "suggestions": MAJOR_CITIES,
    },
    "timeline": {
        "keywords": [
            "when",
            "timeline",
            "urgency",
            "deadline",
            "how soon",
            "by when",
            "expires",
        ],
        "suggestions": TIMELINES,
    },
    "binary": {
        "keywords": [
            "have you",
            "did you",
            "do you",
            "are you",
            "is it",
            "can you",
            "already",
        ],
        "suggestions": YES_NO,
    },
    "documents": {
        "keywords": ["document", "paper", "certificate", "proof", "have your"],
        "suggestions": DOCUMENT_TYPES,
    },
    "language": {
        "keywords": ["language", "speak", "prefer", "understand"],
        "suggestions": LANGUAGES,
    },
}
