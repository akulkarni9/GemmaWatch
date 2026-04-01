import httpx
import os
import json
import base64
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma3:12b")


import asyncio

class AIService:
    def __init__(self):
        # Limit concurrent calls to Ollama to prevent overloading (Gemma 3 is heavy)
        # Increased to 4 to allow chat sessions to run alongside background audits
        self.semaphore = asyncio.Semaphore(4)
        self.default_timeout = 180.0

    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encodes an image to a base64 string for Ollama."""
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"DEBUG: Image encoding failed for {image_path}: {e}")
            return None

    async def _call_ollama(self, prompt: str, is_json: bool = False, images: List[str] = None):
        async with self.semaphore:
            async with httpx.AsyncClient() as client:
                try:
                    print(f"DEBUG: Calling Ollama at {OLLAMA_URL} with model {MODEL_NAME} (is_json={is_json})")
                    
                    payload = {
                        "model": MODEL_NAME,
                        "prompt": prompt,
                        "stream": False
                    }
                    if is_json:
                        payload["format"] = "json"
                    if images:
                        payload["images"] = images
                    
                    response = await client.post(
                        OLLAMA_URL,
                        json=payload,
                        timeout=self.default_timeout
                    )
                    print(f"DEBUG: Ollama response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json().get("response")
                        return result
                    else:
                        return {"error": f"Ollama error: {response.status_code}"} if is_json else f"Ollama error: {response.status_code}"
                except Exception as e:
                    print(f"DEBUG: Ollama call failed - {type(e).__name__}: {str(e)}")
                    return {"error": str(e)} if is_json else f"Error: {str(e)}"

    async def yield_ollama(self, prompt: str, images: List[str] = None):
        """Async generator for real-time token streaming from Ollama."""
        async with self.semaphore:
            async with httpx.AsyncClient() as client:
                try:
                    payload = {
                        "model": MODEL_NAME,
                        "prompt": prompt,
                        "stream": True
                    }
                    if images:
                        payload["images"] = images
                    
                    async with client.stream("POST", OLLAMA_URL, json=payload, timeout=self.default_timeout) as response:
                        if response.status_code != 200:
                            yield f"Error: {response.status_code}"
                            return
                        
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                if "response" in chunk:
                                    yield chunk["response"]
                                if chunk.get("done"):
                                    break
                            except Exception:
                                continue
                except Exception as e:
                    yield f"Stream Error: {str(e)}"

    async def analyze_failure(self, distilled_dom: str, console_logs: list, network_errors: list, error_message: str, screenshot_path: str = None):
        # Format logs for readability
        console_text = "\n".join([f"[{log.get('level', 'log').upper()}] {log.get('message', str(log))}" for log in console_logs]) if console_logs else "No console logs"
        network_text = "\n".join([f"- {err.get('message', str(err))}" for err in network_errors]) if network_errors else "No network errors"
        
        # Gemma 3 has 128k context - we can afford much more than 500 chars
        limit = 5000
        
        visual_context = ""
        images = []
        if screenshot_path:
            encoded = self._encode_image(screenshot_path)
            if encoded:
                images.append(encoded)
                visual_context = "I have uploaded a screenshot of the failure state for your visual analysis."

        prompt = f"""You are an expert Web Reliability Engineer. Analyze this website failure and provide precise, actionable fixes.
{visual_context}

FAILURE DETAILS:
Error: {error_message}

CONSOLE LOGS (last {limit} chars):
{console_text[:limit]}

NETWORK ERRORS:
{network_text[:limit]}

PAGE STRUCTURE:
{distilled_dom[:limit]}

REQUIREMENTS:
1. Identify the root cause with evidence from logs/network errors
2. Assign confidence (0.0-1.0) based on evidence strength
3. Provide SPECIFIC, ACTIONABLE repair steps (not generic advice)
4. Categorize the issue (Frontend, Backend, Network, Database, Infrastructure, etc)
5. Focus on immediate fixes developers can implement

For repair_action, be specific:
- For code issues: "Fix null pointer in payment-form.ts line 42"
- For config issues: "Increase database connection pool from 10 to 50"
- For network issues: "Enable CDN for /api/images endpoint"

Return ONLY valid JSON:
{{
  "probable_cause": "specific root cause with evidence",
  "confidence": 0.9,
  "repair_action": "High-level summary of the fix",
  "category": "Frontend|Backend|Network|Database|Infrastructure",
  "repair_steps": [
    {{
      "id": "step_1",
      "type": "investigate|command|verify",
      "summary": "Short title of the step",
      "content": "Detailed CLI command or manual instruction"
    }}
  ]
}}"""
        
        result = await self._call_ollama(prompt, is_json=True, images=images)
        print(f"DEBUG: Raw result from Gemma: {result}")
        return result

    async def analyze_visual_change(self, baseline_dom: str, current_dom: str, baseline_path: str = None, current_path: str = None):
        images = []
        visual_context = "Comparing DOM structure."
        
        b_encoded = self._encode_image(baseline_path)
        c_encoded = self._encode_image(current_path)
        
        if b_encoded and c_encoded:
            images = [b_encoded, c_encoded]
            visual_context = "I have provided two screenshots: 1) Baseline and 2) Current. Perform a side-by-side visual comparison."

        prompt = f"""
        You are an expert Visual Regression Analyst.
        {visual_context}
        
        Compare the baseline DOM with the current DOM.

        Baseline DOM Sample: {baseline_dom[:2000]}
        Current DOM Sample: {current_dom[:2000]}

        Identify if there are critical regressions (e.g., missing buttons, broken layouts, overlapping text, CSS failures)
        vs. acceptable changes (e.g., text updates, image refreshes).
        
        If images were provided, prioritize visual evidence for layout/rendering issues.

        Return JSON:
        {{
          "is_regression": true|false,
          "severity": "Low|Medium|High",
          "change_summary": "...",
          "impact": "What user action is blocked?"
        }}
        """
        return await self._call_ollama(prompt, is_json=True, images=images)

    async def check_connection(self) -> bool:
        """Check if Ollama is running and Gemma model is available."""
        async with httpx.AsyncClient() as client:
            try:
                # Check Ollama's model list instead of calling generate
                # This is faster and doesn't require model inference
                tags_url = OLLAMA_URL.replace("/api/generate", "/api/tags")
                print(f"DEBUG: Checking Ollama at {tags_url}")
                
                response = await client.get(
                    tags_url,
                    timeout=5.0
                )
                print(f"DEBUG: Ollama /api/tags status: {response.status_code}")
                
                if response.status_code == 200:
                    models_data = response.json()
                    models = models_data.get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    print(f"DEBUG: Available models: {model_names}")
                    
                    # Check if any gemma model is available
                    has_gemma = any("gemma" in name.lower() for name in model_names)
                    print(f"DEBUG: Gemma model found: {has_gemma}")
                    return has_gemma
                    
                return False
                
            except Exception as e:
                print(f"DEBUG: Connection check failed: {str(e)}")
                return False

    async def generate_fingerprint_metadata(self, pattern: str) -> Dict[str, str]:
        """Provides a human-readable title and description for a raw error pattern."""
        prompt = f"""
        Analyze this raw application error pattern and provide a concise, professional, and functional title and description.
        The goal is to group similar technical failures under a single human-readable name.

        Patterns of Error:
        "{pattern}"

        Respond in STRICTOR JSON format only:
        {{
            "title": "A short (3-6 words) technical name for this error (no conversational filler)",
            "description": "A 1-sentence technical explanation of what is failing",
            "severity": "Low|Medium|High"
        }}
        """
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }
            async with self.semaphore:
                async with httpx.AsyncClient() as client:
                    response = await client.post(OLLAMA_URL, json=payload, headers=headers, timeout=self.default_timeout)
                    if response.status_code == 200:
                        data = response.json()
                        metadata_raw = data.get("response", "")
                        if isinstance(metadata_raw, str):
                            try:
                                # Cleanup and parse
                                start_idx = metadata_raw.find('{')
                                end_idx = metadata_raw.rfind('}') + 1
                                if start_idx != -1 and end_idx > start_idx:
                                    return json.loads(metadata_raw[start_idx:end_idx])
                                return json.loads(metadata_raw)
                            except:
                                return None
                        return metadata_raw
                    return None
        except Exception as e:
            print(f"ERROR: AI Fingerprint generation failed: {e}")
            return None


ai_service = AIService()
