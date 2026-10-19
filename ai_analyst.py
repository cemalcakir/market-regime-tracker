import os
import json
import logging
from google import genai

logger = logging.getLogger(__name__)

class AIAnalystService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY not found, AI analysis layer is disabled.")

    def generate_regime_summary(self, regime_data: dict) -> str:
        if not self.client:
            return ""

        prompt = f"""
        You are a senior financial market strategist and algorithmic risk manager.
        Analyze the technical indicators and detected market regime provided below in JSON format.

        Market Data:
        {json.dumps(regime_data, indent=2, ensure_ascii=False)}

        Please provide a concise and readable summary in English (Maximum 3 sentences) following this format:
        🧠 **AI Strategist Commentary:**
        - Main technical rationale for the market state.
        - Key risk standing out in the current regime.
        - Concrete strategic advice for traders.
        """

        try:
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ""