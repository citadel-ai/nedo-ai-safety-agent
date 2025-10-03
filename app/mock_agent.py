"""
Mock agent for deployment environments without Google Cloud credentials.
Provides basic functionality for testing and demonstration.
"""

import time
import uuid
from typing import Dict, Any

from app.deployment_config import get_mock_response

class MockJapanHelpdeskAgent:
    """Mock agent that provides sample responses without requiring AI services."""
    
    def __init__(self):
        self.name = "Mock Japan Helpdesk Agent"
        self.version = "1.0.0-mock"
    
    async def process_query(
        self,
        user_input: str,
        user_id: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Process a user query with mock responses."""
        start_time = time.time()
        session_id = session_id or f"mock_session_{uuid.uuid4().hex[:8]}"
        
        # Simulate processing time
        await self._simulate_processing()
        
        # Generate mock response based on input
        response_text = self._generate_mock_response(user_input)
        
        processing_time = time.time() - start_time
        
        return {
            "response": response_text,
            "confidence_score": 0.8,
            "sources": ["Mock Knowledge Base", "Japan Immigration Guide"],
            "recommendations": [
                "Visit the official immigration website for the most current information",
                "Contact your local city hall for personalized assistance",
                "Consider consulting with an immigration lawyer for complex cases"
            ],
            "session_id": session_id,
            "completed_steps": ["mock_processing", "response_generation"],
            "errors": [],
            "processing_time": processing_time,
            "tokens_used": len(response_text.split()),
            "metadata": {
                "workflow_type": "mock",
                "error_count": 0,
                "fallback_used": True,
                "langfuse_trace_id": None,
                "deployment_mode": True
            }
        }
    
    async def _simulate_processing(self):
        """Simulate AI processing time."""
        import asyncio
        await asyncio.sleep(0.5)  # Simulate 500ms processing
    
    def _generate_mock_response(self, user_input: str) -> str:
        """Generate a contextual mock response based on user input."""
        input_lower = user_input.lower()
        
        if any(keyword in input_lower for keyword in ["visa", "renew", "renewal", "extend"]):
            return """**Visa Renewal Information**

To renew your visa in Japan, you typically need to:

1. **Prepare Required Documents:**
   - Current residence card
   - Passport
   - Certificate of Enrollment (for students) or Employment Certificate (for workers)
   - Tax payment certificates
   - Bank statements showing financial stability

2. **Visit Immigration Office:**
   - Go to your local immigration office 3 months before your visa expires
   - Submit your application with all required documents
   - Pay the application fee (¥4,000 for most visa types)

3. **Processing Time:**
   - Standard processing: 2-4 weeks
   - Busy periods (March-April): Up to 2 months

**Important Notes:**
- Requirements may vary by visa type and individual circumstances
- Always check the official Immigration Services Agency website for current requirements
- This is general guidance only and not legal advice

*Note: This system is currently running in demo mode. For personalized assistance, please ensure proper Google Cloud configuration.*"""
        
        elif any(keyword in input_lower for keyword in ["work", "job", "employment", "バイト"]):
            return """**Working in Japan Information**

**For Students:**
- Need "Permission to Engage in Activity Other than Permitted" (資格外活動許可)
- Maximum 28 hours per week
- Apply at immigration office with your student ID

**For Other Visa Holders:**
- Check your residence card for work permissions
- Some visas allow unlimited work, others have restrictions
- Changing job types may require visa status change

**Job Search Tips:**
- Use job boards like Indeed Japan, Rikunabi, MyNavi
- Consider language requirements for your field
- Networking through professional associations
- Hello Work (public employment service) offers free support

*Note: This system is currently running in demo mode. For personalized assistance, please ensure proper Google Cloud configuration.*"""
        
        elif any(keyword in input_lower for keyword in ["health", "insurance", "hospital", "医療"]):
            return """**Healthcare in Japan**

**Health Insurance:**
- All residents must enroll in health insurance
- National Health Insurance (国民健康保険) for most foreigners
- Covers 70% of medical costs

**Using Healthcare:**
- Bring your insurance card to any clinic/hospital
- Pay 30% of costs at point of service
- Emergency: Call 119 for ambulance

**Common Services:**
- Regular checkups at local clinics
- Prescription medicine from pharmacies (薬局)
- Dental care (often separate insurance)

**Language Support:**
- Some hospitals have English-speaking staff
- Medical interpretation services available
- Translation apps can help with basic communication

*Note: This system is currently running in demo mode. For personalized assistance, please ensure proper Google Cloud configuration.*"""
        
        else:
            return f"""**Japan Living Assistance**

Thank you for your question about: "{user_input}"

I'm here to help with information about living in Japan, including:
- Visa and immigration matters
- Work and employment
- Healthcare and insurance  
- Housing and daily life
- Government procedures
- Cultural guidance

**Current Status:** This system is running in demonstration mode. While I can provide general information, the full AI-powered assistance requires proper Google Cloud configuration.

**For immediate help:**
- Visit your local city hall (市役所) for official guidance
- Check the Immigration Services Agency website: https://www.moj.go.jp/isa/
- Contact JHELP (0570-000-911) for multilingual support

Please feel free to ask more specific questions about any aspect of life in Japan!

*Note: This is general guidance only and not legal advice.*"""

# Create a global instance for easy import
mock_agent = MockJapanHelpdeskAgent()
