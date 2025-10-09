# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# mypy: ignore-errors
import pytest
from app.agent import JapanHelpdeskAgent

agent = JapanHelpdeskAgent().agent


@pytest.mark.asyncio
async def test_agent_process_query() -> None:
    """
    Integration test for the working agent query processing.
    Tests that the agent returns valid responses.
    """
    result = await agent.process_query(
        user_input="How do I renew my visa in Japan?",
        user_id="test_user",
        session_id="test_session",
    )

    # Verify response structure
    assert "response" in result
    assert "confidence_score" in result
    assert "session_id" in result

    # Verify we got a response
    assert len(result["response"]) > 0, "Expected non-empty response"

    # Verify confidence score is reasonable
    assert 0.0 <= result["confidence_score"] <= 1.0, (
        "Confidence score should be between 0 and 1"
    )
