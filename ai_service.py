import os
import json
import logging

try:
    from google import genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

class MarketAIAnalyst:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.client = None
                logger.error(f"Failed to initialize GenAI client: {e}")
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY not found or genai module missing.")

    def generate_commentary(self, asset_name: str, metrics: dict) -> str:
        if not self.client:
            return "AI commentary disabled (Client not initialized)."

        prompt = f"""
        You are a senior financial market strategist and quantitative risk manager. 
        Analyze the technical indicators and market metrics for {asset_name} provided below in JSON format:

        {json.dumps(metrics, indent=2, ensure_ascii=False)}

        Provide a concise, professional market commentary in English (Max 3 sentences):
        1. Summary of current technical state relative to indicators.
        2. Key risk or threshold to watch out for.
        3. Strategic takeaway for traders.
        """

        try:
            response = self.client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_msg = f"AI generation error: {e}"
            logger.error(error_msg)
            return error_msg