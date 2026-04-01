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
@pytest.mark.asyncio
async def test_chat_multimodal_attachment(temp_db):
    """Verify that screenshots are attached when a site matches."""
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO sites (id, name, url) VALUES (?, ?, ?)", ("site-1", "Mark", "https://mark.com"))
    conn.execute("INSERT INTO checks (id, site_id, status, timestamp, screenshot_url) VALUES (?, ?, ?, ?, ?)", 
                 ("check-1", "site-1", "SUCCESS", "2024-01-01T00:00:00", "/screenshots/currents/mark_123.png"))
    conn.commit()
    conn.close()

    # Mock file system and AI encoding
    with patch("os.path.exists", return_value=True):
        with patch("services.ai_service.AIService._encode_image", return_value="encoded_image_data") as mock_encode:
            with patch("services.chat_service._structured_query", new_callable=AsyncMock) as mock_struct:
                mock_struct.return_value = {"answer": "See image", "query_type": "structured"}
                
                await chat("Show me Mark", session_id="test-session")
                
                # Check if _structured_query was called with the image
                args, kwargs = mock_struct.call_args
                assert kwargs["images"] == ["encoded_image_data"]

@pytest.mark.asyncio
async def test_chat_big_context_handling():
    """Verify that _structured_query handles a large data context."""
    from services.chat_service import _structured_query
    
    # Create a large dummy string (approx 60k chars)
    big_data = [{"id": i, "content": "x" * 100} for i in range(600)]
    
    with patch("services.ai_service.AIService._call_ollama", new_callable=AsyncMock) as mock_ai:
        # First call returns SQL, second call returns answer
        mock_ai.side_effect = ["SELECT * FROM sites", "Summary"]
        
        # Mock DB connection and result
        with patch("services.chat_service._get_conn") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchmany.return_value = big_data
            
            await _structured_query("Summarize everything")
            
            # Verify that the format_prompt received truncated data (15k)
            # _call_ollama is called twice: SQL and Formatting. We want the second.
            call_list = mock_ai.call_args_list
            assert len(call_list) == 2
            
            prompt = call_list[1][0][0]
            assert "DATA CONTEXT (UP TO 15k CHARS)" in prompt
            # Check length of prompt (should be around 15k + overhead)
            assert len(prompt) > 10000
