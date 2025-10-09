"""
Facts Extractor - Transform state into UI-displayable collected facts.

This module provides a clean interface for extracting and formatting
collected information for display in the UI sidebar.
"""

from dataclasses import dataclass
from typing import Any

from src.models import IntakeSession, JapanHelpdeskState


@dataclass
class DisplayFact:
    """A single fact to display in the UI."""
    key: str  # Internal key (e.g., "user_location")
    label: str  # Human-readable label (e.g., "Location")
    value: str  # Display value
    icon: str | None = None  # Optional icon identifier for UI
    confidence: str | None = None  # Optional confidence level


@dataclass
class CollectedFacts:
    """Structured collection of facts for UI display."""
    
    # Core request information
    main_request: DisplayFact | None = None
    category: DisplayFact | None = None
    
    # Location information
    location: DisplayFact | None = None
    specific_office: DisplayFact | None = None
    
    # Visa/Status information
    visa_type: DisplayFact | None = None
    current_status: DisplayFact | None = None
    
    # Timeline information
    timeline: DisplayFact | None = None
    urgency: DisplayFact | None = None
    
    # Additional context
    language_preference: DisplayFact | None = None
    previous_attempts: DisplayFact | None = None
    
    # Completion status
    is_complete: bool = False
    needs_clarification: list[str] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"is_complete": self.is_complete}
        
        # Add all non-None facts
        facts = []
        for field_name in [
            "main_request",
            "category",
            "location",
            "specific_office",
            "visa_type",
            "current_status",
            "timeline",
            "urgency",
            "language_preference",
            "previous_attempts",
        ]:
            fact = getattr(self, field_name, None)
            if fact:
                facts.append({
                    "key": fact.key,
                    "label": fact.label,
                    "value": fact.value,
                    "icon": fact.icon,
                    "confidence": fact.confidence,
                })
        
        result["facts"] = facts
        
        if self.needs_clarification:
            result["needs_clarification"] = self.needs_clarification
        
        return result


class FactsExtractor:
    """Extract and format collected facts from state."""
    
    # Mapping of keys to human-readable labels and icons
    FACT_METADATA = {
        "main_request": {"label": "Main Request", "icon": "message"},
        "category": {"label": "Category", "icon": "folder"},
        "user_location": {"label": "Location", "icon": "map-pin"},
        "location": {"label": "Location", "icon": "map-pin"},
        "specific_office_needed": {"label": "Office Needed", "icon": "building"},
        "visa_type": {"label": "Visa Type", "icon": "card"},
        "current_status": {"label": "Current Status", "icon": "info"},
        "timeline": {"label": "Timeline", "icon": "calendar"},
        "urgency_level": {"label": "Urgency", "icon": "alert-circle"},
        "language_preference": {"label": "Language", "icon": "globe"},
        "previous_attempts": {"label": "Previous Attempts", "icon": "clock"},
    }
    
    def extract_from_state(self, state: JapanHelpdeskState) -> CollectedFacts:
        """
        Extract collected facts from state for UI display.
        
        Args:
            state: Current workflow state
            
        Returns:
            CollectedFacts object ready for UI display
        """
        intake = state.get("intake_session")
        if not intake:
            return CollectedFacts(is_complete=False)
        
        return self.extract_from_session(intake)
    
    def extract_from_session(self, session: IntakeSession) -> CollectedFacts:
        """
        Extract collected facts from intake session.
        
        Args:
            session: IntakeSession object
            
        Returns:
            CollectedFacts object ready for UI display
        """
        facts = CollectedFacts(
            is_complete=session.is_complete,
            needs_clarification=session.needs_clarification if session.needs_clarification else None
        )
        
        # Extract from collected_info dict
        collected = session.collected_info or {}
        
        # Main request
        if main_req := collected.get("main_request"):
            facts.main_request = self._create_fact("main_request", str(main_req))
        
        # Category (from scope_check_result if available)
        if category := collected.get("category"):
            facts.category = self._create_fact("category", str(category))
        
        # Location - check multiple sources
        location = (
            collected.get("location") 
            or collected.get("user_location") 
            or session.user_location
        )
        if location:
            facts.location = self._create_fact("user_location", str(location))
        
        # Specific office
        if office := (collected.get("specific_office_needed") or session.specific_office_needed):
            facts.specific_office = self._create_fact("specific_office_needed", str(office))
        
        # Visa information
        if visa := (collected.get("visa_type") or session.visa_type):
            facts.visa_type = self._create_fact("visa_type", str(visa))
        
        # Current status
        if status := (collected.get("current_status") or session.current_status):
            facts.current_status = self._create_fact("current_status", str(status))
        
        # Timeline
        if timeline := (collected.get("timeline") or session.timeline):
            facts.timeline = self._create_fact("timeline", str(timeline))
        
        # Urgency
        if urgency := (collected.get("urgency_level") or session.urgency_level):
            facts.urgency = self._create_fact("urgency_level", str(urgency))
        
        # Language preference
        if lang := (collected.get("language_preference") or session.language_preference):
            facts.language_preference = self._create_fact("language_preference", str(lang))
        
        # Previous attempts
        if attempts := (collected.get("previous_attempts") or session.previous_attempts):
            facts.previous_attempts = self._create_fact("previous_attempts", str(attempts))
        
        return facts
    
    def _create_fact(self, key: str, value: str, confidence: str | None = None) -> DisplayFact:
        """Create a DisplayFact with metadata."""
        metadata = self.FACT_METADATA.get(key, {"label": key.replace("_", " ").title(), "icon": None})
        
        return DisplayFact(
            key=key,
            label=metadata["label"],
            value=value,
            icon=metadata.get("icon"),
            confidence=confidence
        )


# Global singleton instance
_facts_extractor = FactsExtractor()


def get_facts_extractor() -> FactsExtractor:
    """Get the global facts extractor instance."""
    return _facts_extractor


def extract_display_facts(state: JapanHelpdeskState) -> dict[str, Any]:
    """
    Convenience function to extract facts from state as a dictionary.
    
    This is the main function to use when adding facts to API responses.
    
    Usage in API:
        from src.utils.facts_extractor import extract_display_facts
        
        response = {
            "message": "...",
            "collected_facts": extract_display_facts(state)
        }
    """
    extractor = get_facts_extractor()
    facts = extractor.extract_from_state(state)
    return facts.to_dict()

