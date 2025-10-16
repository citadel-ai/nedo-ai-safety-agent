"""
Safety evaluation module for PII detection and content safety checks.

Implements enterprise-grade safety guardrails for AI agent responses.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class PIIType(Enum):
    """Types of personally identifiable information."""
    EMAIL = "email"
    PHONE = "phone"
    MY_NUMBER = "my_number"
    PASSPORT = "passport"
    ADDRESS = "address"
    NAME = "name"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"


@dataclass
class PIIMatch:
    """A detected PII instance."""
    pii_type: PIIType
    text: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class PIIDetectionResult:
    """Result of PII detection analysis."""
    has_pii: bool
    matches: List[PIIMatch]
    pii_types: List[str]
    risk_level: str  # 'none', 'low', 'medium', 'high'
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "has_pii": self.has_pii,
            "pii_count": len(self.matches),
            "pii_types": self.pii_types,
            "risk_level": self.risk_level,
            "matches": [
                {
                    "type": m.pii_type.value,
                    "text": m.text[:20] + "..." if len(m.text) > 20 else m.text,
                    "position": f"{m.start}-{m.end}",
                    "confidence": m.confidence
                }
                for m in self.matches
            ]
        }


class PIIDetector:
    """
    PII detection with support for both English and Japanese patterns.
    
    Detects:
    - Email addresses
    - Phone numbers (Japanese and international)
    - My Number (マイナンバー) - 12-digit Japanese ID
    - Passport numbers
    - Japanese addresses
    - Credit card numbers
    - Bank account numbers
    """
    
    # Regex patterns for PII detection
    PATTERNS = {
        PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        
        # Japanese phone: 090-1234-5678, 03-1234-5678, 0312345678
        PIIType.PHONE: r'(?:\+81[-\s]?|0)(?:\d{1,4}[-\s]?\d{1,4}[-\s]?\d{4}|\d{9,11})',
        
        # My Number: 12-digit number (may have spaces or hyphens)
        PIIType.MY_NUMBER: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        
        # Passport: typically 2 letters + 7 digits (varies by country)
        PIIType.PASSPORT: r'\b[A-Z]{1,2}\d{7,9}\b',
        
        # Credit card: 13-19 digits with optional spaces/hyphens
        PIIType.CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{3,4}\b',
        
        # Bank account: varies, but looking for 7-8 digit sequences
        PIIType.BANK_ACCOUNT: r'\b(?:口座番号|account|口座)[:\s]*(\d{7,8})\b',
    }
    
    # Japanese address patterns (more complex, using partial matching)
    ADDRESS_KEYWORDS = [
        '都', '道', '府', '県',  # Prefecture suffixes
        '市', '区', '町', '村',  # City/ward suffixes
        '丁目', '番地', '号',    # Address components
        '〒',                    # Postal mark
    ]
    
    def __init__(self):
        """Initialize PII detector."""
        self.enabled = Config.PII_DETECTION_ENABLED
        self.masking_mode = Config.PII_MASKING_MODE
        
        if not self.enabled:
            logger.info("PII detection is disabled")
    
    def detect_pii(self, text: str) -> PIIDetectionResult:
        """
        Detect PII in the given text.
        
        Args:
            text: Text to scan for PII
            
        Returns:
            PIIDetectionResult with detected PII instances
        """
        if not self.enabled or not text:
            return PIIDetectionResult(
                has_pii=False,
                matches=[],
                pii_types=[],
                risk_level='none'
            )
        
        matches: List[PIIMatch] = []
        
        # Run regex patterns
        for pii_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Additional validation for specific types
                if self._validate_match(pii_type, match.group()):
                    matches.append(PIIMatch(
                        pii_type=pii_type,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=self._calculate_confidence(pii_type, match.group())
                    ))
        
        # Detect Japanese addresses (keyword-based)
        address_matches = self._detect_japanese_addresses(text)
        matches.extend(address_matches)
        
        # Calculate risk level
        pii_types = list(set(m.pii_type.value for m in matches))
        risk_level = self._calculate_risk_level(matches)
        
        result = PIIDetectionResult(
            has_pii=len(matches) > 0,
            matches=matches,
            pii_types=pii_types,
            risk_level=risk_level
        )
        
        if result.has_pii:
            logger.warning(f"PII detected: {len(matches)} instances, types: {pii_types}, risk: {risk_level}")
        
        return result
    
    def _validate_match(self, pii_type: PIIType, text: str) -> bool:
        """
        Validate a potential PII match to reduce false positives.
        
        Args:
            pii_type: Type of PII
            text: Matched text
            
        Returns:
            True if match is likely valid PII
        """
        # My Number: must be exactly 12 digits (with optional separators)
        if pii_type == PIIType.MY_NUMBER:
            digits = re.sub(r'[-\s]', '', text)
            return len(digits) == 12
        
        # Credit card: basic Luhn algorithm check
        if pii_type == PIIType.CREDIT_CARD:
            digits = re.sub(r'[-\s]', '', text)
            return len(digits) in [13, 14, 15, 16, 19] and self._luhn_check(digits)
        
        # Phone: must have at least 10 digits
        if pii_type == PIIType.PHONE:
            digits = re.sub(r'[-\s+]', '', text)
            return len(digits) >= 10
        
        return True
    
    def _luhn_check(self, card_number: str) -> bool:
        """
        Validate credit card using Luhn algorithm.
        
        Args:
            card_number: Credit card number (digits only)
            
        Returns:
            True if valid according to Luhn
        """
        try:
            digits = [int(d) for d in card_number]
            checksum = 0
            for i, d in enumerate(reversed(digits)):
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                checksum += d
            return checksum % 10 == 0
        except:
            return False
    
    def _detect_japanese_addresses(self, text: str) -> List[PIIMatch]:
        """
        Detect Japanese addresses using keyword matching.
        
        Args:
            text: Text to scan
            
        Returns:
            List of address matches
        """
        matches = []
        
        # Look for address indicators
        for keyword in self.ADDRESS_KEYWORDS:
            if keyword in text:
                # Find surrounding context (up to 50 chars before and after)
                for match in re.finditer(re.escape(keyword), text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    
                    # Extract address-like substring
                    address_text = text[start:end].strip()
                    
                    matches.append(PIIMatch(
                        pii_type=PIIType.ADDRESS,
                        text=address_text,
                        start=start,
                        end=end,
                        confidence=0.7  # Lower confidence for keyword-based
                    ))
                    break  # Only one match per keyword
        
        return matches
    
    def _calculate_confidence(self, pii_type: PIIType, text: str) -> float:
        """
        Calculate confidence score for PII match.
        
        Args:
            pii_type: Type of PII
            text: Matched text
            
        Returns:
            Confidence score (0-1)
        """
        # High confidence for well-structured patterns
        if pii_type in [PIIType.EMAIL, PIIType.CREDIT_CARD]:
            return 0.95
        
        # Medium confidence for numeric patterns
        if pii_type in [PIIType.PHONE, PIIType.MY_NUMBER]:
            return 0.85
        
        # Lower confidence for addresses (many false positives)
        if pii_type == PIIType.ADDRESS:
            return 0.70
        
        return 0.80
    
    def _calculate_risk_level(self, matches: List[PIIMatch]) -> str:
        """
        Calculate overall risk level based on detected PII.
        
        Args:
            matches: List of PII matches
            
        Returns:
            Risk level: 'none', 'low', 'medium', 'high'
        """
        if not matches:
            return 'none'
        
        # High-risk PII types
        high_risk_types = {PIIType.MY_NUMBER, PIIType.PASSPORT, PIIType.CREDIT_CARD, PIIType.BANK_ACCOUNT}
        has_high_risk = any(m.pii_type in high_risk_types for m in matches)
        
        if has_high_risk:
            return 'high'
        elif len(matches) > 3:
            return 'medium'
        elif len(matches) > 1:
            return 'low'
        else:
            # Check confidence
            avg_confidence = sum(m.confidence for m in matches) / len(matches)
            return 'medium' if avg_confidence > 0.9 else 'low'
    
    def mask_pii(self, text: str, result: PIIDetectionResult) -> str:
        """
        Mask detected PII in text.
        
        Args:
            text: Original text
            result: PII detection result
            
        Returns:
            Text with PII masked
        """
        if not result.has_pii or self.masking_mode != 'mask_output':
            return text
        
        # Sort matches by position (reverse order to preserve indices)
        sorted_matches = sorted(result.matches, key=lambda m: m.start, reverse=True)
        
        masked_text = text
        for match in sorted_matches:
            # Create mask based on PII type
            mask = self._create_mask(match.pii_type, match.text)
            masked_text = masked_text[:match.start] + mask + masked_text[match.end:]
        
        return masked_text
    
    def _create_mask(self, pii_type: PIIType, text: str) -> str:
        """
        Create an appropriate mask for PII.
        
        Args:
            pii_type: Type of PII
            text: Original PII text
            
        Returns:
            Masked version
        """
        if pii_type == PIIType.EMAIL:
            # Keep first char and domain
            parts = text.split('@')
            if len(parts) == 2:
                return f"{parts[0][0]}***@{parts[1]}"
        
        if pii_type == PIIType.PHONE:
            # Keep last 4 digits
            digits = re.sub(r'[-\s+]', '', text)
            return f"***-***-{digits[-4:]}" if len(digits) >= 4 else "***"
        
        if pii_type in [PIIType.MY_NUMBER, PIIType.PASSPORT, PIIType.CREDIT_CARD]:
            # Completely mask sensitive IDs
            return "[REDACTED]"
        
        if pii_type == PIIType.ADDRESS:
            return "[ADDRESS REDACTED]"
        
        # Default: mask with asterisks
        return "*" * min(len(text), 10)


@dataclass
class SafetyCheckResult:
    """Result of content safety analysis."""
    is_safe: bool
    safety_score: float  # 0-1, higher is safer
    toxicity_score: float  # 0-1, higher is more toxic
    has_hallucination_risk: bool
    issues: List[str]
    citation_coverage: float  # 0-1, % of answer grounded in citations
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "is_safe": self.is_safe,
            "safety_score": self.safety_score,
            "toxicity_score": self.toxicity_score,
            "has_hallucination_risk": self.has_hallucination_risk,
            "citation_coverage": self.citation_coverage,
            "issues": self.issues,
        }


class ContentSafetyChecker:
    """
    Content safety checker for AI-generated responses.
    
    Checks for:
    - Toxic or harmful content
    - Biased language
    - Hallucination risk (claims not grounded in citations)
    - Misinformation indicators
    """
    
    # Keywords that may indicate problematic content
    TOXIC_KEYWORDS = [
        'illegal', 'fraud', 'scam', 'fake',
        # Add more as needed
    ]
    
    BIAS_KEYWORDS = [
        # Nationality/ethnicity biases
        'all foreigners', 'those people',
        # Add more as needed
    ]
    
    def __init__(self):
        """Initialize content safety checker."""
        self.safety_threshold = Config.SAFETY_SCORE_THRESHOLD
    
    def check_safety(
        self,
        text: str,
        citations: Optional[List[dict]] = None,
        metadata: Optional[dict] = None
    ) -> SafetyCheckResult:
        """
        Check content safety of generated text.
        
        Args:
            text: Generated text to check
            citations: List of citations (if available)
            metadata: Additional metadata (e.g., Vertex AI safety scores)
            
        Returns:
            SafetyCheckResult with safety analysis
        """
        issues = []
        
        # Check for toxic content (basic keyword matching)
        toxicity_score = self._check_toxicity(text)
        if toxicity_score > 0.3:
            issues.append(f"Potential toxic content (score: {toxicity_score:.2f})")
        
        # Check for bias
        bias_score = self._check_bias(text)
        if bias_score > 0.3:
            issues.append(f"Potential bias detected (score: {bias_score:.2f})")
        
        # Check citation coverage (hallucination risk)
        citation_coverage = self._calculate_citation_coverage(text, citations)
        has_hallucination_risk = citation_coverage < Config.MIN_CITATION_COVERAGE
        if has_hallucination_risk:
            issues.append(f"Low citation coverage ({citation_coverage:.2%}), possible hallucination")
        
        # Calculate overall safety score
        safety_score = self._calculate_safety_score(
            toxicity_score, bias_score, citation_coverage
        )
        
        is_safe = safety_score >= self.safety_threshold and not has_hallucination_risk
        
        result = SafetyCheckResult(
            is_safe=is_safe,
            safety_score=safety_score,
            toxicity_score=toxicity_score,
            has_hallucination_risk=has_hallucination_risk,
            issues=issues,
            citation_coverage=citation_coverage
        )
        
        if not is_safe:
            logger.warning(f"Safety check failed: score={safety_score:.2f}, issues={issues}")
        
        return result
    
    def _check_toxicity(self, text: str) -> float:
        """
        Check for toxic content using keyword matching.
        
        Args:
            text: Text to check
            
        Returns:
            Toxicity score (0-1)
        """
        text_lower = text.lower()
        toxic_count = sum(1 for keyword in self.TOXIC_KEYWORDS if keyword in text_lower)
        
        # Normalize by text length (per 100 words)
        words = len(text.split())
        normalized_score = (toxic_count / max(words / 100, 1)) * 0.5
        
        return min(normalized_score, 1.0)
    
    def _check_bias(self, text: str) -> float:
        """
        Check for biased language.
        
        Args:
            text: Text to check
            
        Returns:
            Bias score (0-1)
        """
        text_lower = text.lower()
        bias_count = sum(1 for keyword in self.BIAS_KEYWORDS if keyword in text_lower)
        
        # Normalize
        words = len(text.split())
        normalized_score = (bias_count / max(words / 100, 1)) * 0.5
        
        return min(normalized_score, 1.0)
    
    def _calculate_citation_coverage(
        self,
        text: str,
        citations: Optional[List[dict]]
    ) -> float:
        """
        Calculate what % of the answer is grounded in citations.
        
        Args:
            text: Generated text
            citations: List of citations
            
        Returns:
            Citation coverage score (0-1)
        """
        if not citations:
            return 0.0
        
        # Count citation markers in text [1], [2], etc.
        citation_markers = re.findall(r'\[\d+\]', text)
        
        if not citation_markers:
            return 0.0
        
        # Estimate coverage based on citation density
        # Assumption: 1 citation per ~50 words is well-grounded
        words = len(text.split())
        expected_citations = max(words / 50, 1)
        actual_citations = len(set(citation_markers))
        
        coverage = min(actual_citations / expected_citations, 1.0)
        
        return coverage
    
    def _calculate_safety_score(
        self,
        toxicity_score: float,
        bias_score: float,
        citation_coverage: float
    ) -> float:
        """
        Calculate overall safety score.
        
        Args:
            toxicity_score: Toxicity score (0-1)
            bias_score: Bias score (0-1)
            citation_coverage: Citation coverage (0-1)
            
        Returns:
            Overall safety score (0-1, higher is safer)
        """
        # Invert toxicity and bias (higher is worse)
        toxicity_safety = 1.0 - toxicity_score
        bias_safety = 1.0 - bias_score
        
        # Weighted average
        safety_score = (
            toxicity_safety * 0.4 +
            bias_safety * 0.3 +
            citation_coverage * 0.3
        )
        
        return safety_score


class SafetyEvaluator:
    """
    Combined safety evaluator integrating PII detection and content safety.
    """
    
    def __init__(self):
        """Initialize safety evaluator."""
        self.pii_detector = PIIDetector()
        self.content_checker = ContentSafetyChecker()
    
    def evaluate(
        self,
        text: str,
        citations: Optional[List[dict]] = None,
        check_pii: bool = True,
        check_content: bool = True
    ) -> Dict[str, any]:
        """
        Perform comprehensive safety evaluation.
        
        Args:
            text: Text to evaluate
            citations: Optional citations list
            check_pii: Whether to check for PII
            check_content: Whether to check content safety
            
        Returns:
            Dictionary with evaluation results
        """
        results = {
            "text_length": len(text),
            "word_count": len(text.split()),
        }
        
        # PII detection
        if check_pii:
            pii_result = self.pii_detector.detect_pii(text)
            results["pii"] = pii_result.to_dict()
            
            # Mask if needed
            if pii_result.has_pii and self.pii_detector.masking_mode == 'mask_output':
                results["masked_text"] = self.pii_detector.mask_pii(text, pii_result)
        
        # Content safety
        if check_content:
            safety_result = self.content_checker.check_safety(text, citations)
            results["safety"] = safety_result.to_dict()
        
        # Overall pass/fail
        results["passed"] = (
            (not check_pii or not results.get("pii", {}).get("has_pii")) and
            (not check_content or results.get("safety", {}).get("is_safe", True))
        )
        
        return results

