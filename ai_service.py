import os
import json
import logging
from google import genai

logger = logging.getLogger(__name__)

class MarketAIAnalyst:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY not found, AI commentary will use fallback.")

    def generate_commentary(self, asset_name: str, metrics: dict) -> str:
        if not self.client:
            return "AI analysis unavailable (Missing API Key)."

        prompt = f"""
        You are a senior financial market strategist and quantitative risk manager. 
        Analyze the technical indicators for {asset_name} provided below in JSON format:

        {json.dumps(metrics, indent=2, ensure_ascii=False)}

        Provide a concise, professional market commentary in English (Max 3 sentences):
        1. Summary of current technical state.
        2. Key risk to watch.
        3. Strategic takeaway for traders.
        """

        try:
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error for {asset_name}: {e}")
            return f"AI generation error: {str(e)}"