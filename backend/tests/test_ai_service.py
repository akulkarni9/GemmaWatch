import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.ai_service import AIService
import os

@pytest.fixture
def ai_service():
    return AIService()

@pytest.mark.asyncio
async def test_call_ollama_payload(ai_service):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"response": "test response"})
        
        prompt = "test prompt"
        await ai_service._call_ollama(prompt, is_json=True, images=["base64_data"])
        
        # Verify the payload sent to Ollama
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert payload["prompt"] == prompt
        assert payload["format"] == "json"
        assert payload["images"] == ["base64_data"]
        assert payload["stream"] is False

@pytest.mark.asyncio
async def test_analyze_failure_with_screenshot(ai_service):
    with patch.object(AIService, "_encode_image", return_value="fake_base64"):
        with patch.object(AIService, "_call_ollama", AsyncMock(return_value={"probable_cause": "test"})) as mock_call:
            await ai_service.analyze_failure("dom", [], [], "error", screenshot_path="path/to/img.png")
            
            # Verify call to _call_ollama
            mock_call.assert_called_once()
            args, kwargs = mock_call.call_args
            assert "uploaded a screenshot" in args[0]
            assert kwargs["images"] == ["fake_base64"]

@pytest.mark.asyncio
async def test_analyze_visual_change_with_images(ai_service):
    def mock_encode(path):
        return f"base64_{path}" if path else None

    with patch.object(AIService, "_encode_image", side_effect=mock_encode):
        with patch.object(AIService, "_call_ollama", AsyncMock(return_value={"is_regression": False})) as mock_call:
            await ai_service.analyze_visual_change(
                "baseline_dom", "current_dom", 
                baseline_path="b.png", current_path="c.png"
            )
            
            # Verify call to _call_ollama
            mock_call.assert_called_once()
            args, kwargs = mock_call.call_args
            assert "two screenshots" in args[0]
            assert "base64_b.png" in kwargs["images"]
            assert "base64_c.png" in kwargs["images"]

def test_generate_fingerprint_metadata_uses_env_model(ai_service):
    # This one is tricky because it's async but uses a different pattern in the code
    # Let's just verify the logic locally if possible or mock the httpx call
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"response": "{}"})
        
        # Mock MODEL_NAME
        with patch("services.ai_service.MODEL_NAME", "custom-model"):
            import asyncio
            asyncio.run(ai_service.generate_fingerprint_metadata("pattern"))
            
            args, kwargs = mock_post.call_args
            assert kwargs["json"]["model"] == "custom-model"
