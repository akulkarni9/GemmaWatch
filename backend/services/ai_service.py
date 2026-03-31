import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma:latest")


class AIService:
    async def _call_ollama(self, prompt: str, is_json: bool = False):
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
                
                response = await client.post(
                    OLLAMA_URL,
                    json=payload,
                    timeout=60.0
                )
                print(f"DEBUG: Ollama response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json().get("response")
                    print(f"DEBUG: Ollama response: {result}")
                    return result
                else:
                    # Log the full error response
                    try:
                        error_body = response.json()
                        print(f"DEBUG: Ollama error body: {error_body}")
                    except:
                        print(f"DEBUG: Ollama error text: {response.text}")
                    print(f"DEBUG: Ollama error - status {response.status_code}")
                    return {"error": f"Ollama error: {response.status_code}"} if is_json else f"Ollama error: {response.status_code}"
            except Exception as e:
                print(f"DEBUG: Ollama call failed - {type(e).__name__}: {str(e)}")
                return {"error": str(e)} if is_json else f"Error: {str(e)}"

    async def analyze_failure(self, distilled_dom: str, console_logs: list, network_errors: list, error_message: str):
        # Format logs for readability
        console_text = "\n".join([f"[{log.get('level', 'log').upper()}] {log.get('message', str(log))}" for log in console_logs]) if console_logs else "No console logs"
        network_text = "\n".join([f"- {err.get('message', str(err))}" for err in network_errors]) if network_errors else "No network errors"
        
        prompt = f"""You are an expert Web Reliability Engineer. Analyze this website failure and provide precise, actionable fixes.

FAILURE DETAILS:
Error: {error_message}

CONSOLE LOGS (last 500 chars):
{console_text[:500]}

NETWORK ERRORS:
{network_text[:500]}

PAGE STRUCTURE:
{distilled_dom[:500]}

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
  "repair_action": "specific, actionable fix",
  "category": "Frontend|Backend|Network|Database|Infrastructure"
}}"""
        
        result = await self._call_ollama(prompt, is_json=True)
        print(f"DEBUG: Raw result from Gemma: {result}")
        return result

    async def analyze_visual_change(self, baseline_dom: str, current_dom: str):
        prompt = f"""
        You are an expert Visual Regression Analyst.
        Compare the baseline DOM with the current DOM.

        Baseline: {baseline_dom}
        Current: {current_dom}

        Identify if there are critical regressions (e.g., missing buttons, broken layouts)
        vs. acceptable changes (e.g., text updates).

        Return JSON:
        {{
          "is_regression": true|false,
          "severity": "Low|Medium|High",
          "change_summary": "...",
          "impact": "What user action is blocked?"
        }}
        """
        return await self._call_ollama(prompt, is_json=True)

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


ai_service = AIService()
