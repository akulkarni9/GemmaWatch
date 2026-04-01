import pytest
import sqlite3
from unittest.mock import AsyncMock, patch
from services.chat_service import chat, _detect_site_match

@pytest.mark.asyncio
async def test_detect_site_match_success(temp_db):
    """Verify that existing site names are correctly detected in prompts."""
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO sites (id, name, url) VALUES (?, ?, ?)", ("site-1", "Mark Production", "https://mark.com"))
    conn.commit()
    conn.close()
    
    # 1. Exact match (returns list)
    match = _detect_site_match("Tell me about Mark Production")
    assert "Mark Production" in match
    
    # 2. No match (returns empty list)
    match = _detect_site_match("Tell me about a random site")
    assert match == []

@pytest.mark.asyncio
async def test_chat_routing_structured(temp_db):
    """Verify that site-specific queries are routed to 'structured' path."""
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO sites (id, name, url) VALUES (?, ?, ?)", ("site-1", "Mark", "https://mark.com"))
    conn.commit()
    conn.close()
    
    # Global patch for the AI service call
    with patch("services.ai_service.AIService._call_ollama", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = 'SELECT status FROM sites WHERE name = "Mark"'
        
        # Partially mock the response to verify the router logic
        with patch("services.chat_service._structured_query", new_callable=AsyncMock) as mock_struct:
            mock_struct.return_value = {"answer": "Mark is ONLINE", "query_type": "structured", "sources": []}
            
            response = await chat("How is Mark?", session_id="test-session")
            assert response["query_type"] == "structured"
            assert "ONLINE" in response["answer"]

@pytest.mark.asyncio
async def test_chat_routing_system(temp_db):
    """Verify that help/capabilities queries are routed to 'system' path."""
    with patch("services.ai_service.AIService._call_ollama", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = "I am the GemmaWatch Analyst. I can monitor your sites."
        
        # Need to ensure classification routes to system
        with patch("services.chat_service._classify_query", new_callable=AsyncMock) as mock_class:
            mock_class.return_value = "system"
            
            response = await chat("What can you do?", session_id="test-session")
            assert response["query_type"] == "system"
            assert "Analyst" in response["answer"]
