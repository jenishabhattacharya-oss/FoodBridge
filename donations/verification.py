import json

import requests
from django.conf import settings


class FoodSafetyVerifier:
    """Provider boundary for visible food-condition screening."""

    provider_name = "gemini"

    def verify(self, photos, *, is_unpackaged):
        if not settings.GEMINI_API_KEY:
            return {"decision": "review", "confidence": 0, "summary": "AI screening is not configured; this donation needs human review.", "risk_flags": ["verification_unavailable"]}
        parts = [{"text": "You screen food-donation images for only visible warning signs. You cannot certify food safety. Return JSON only with decision (approve, reject, review), confidence (0-100), summary for donor, and risk_flags array. Reject only clear visible spoilage, mold, pests, leaking/damaged packaging, or visibly unsafe handling. Review when image quality/evidence is insufficient. " + ("Food is unpackaged." if is_unpackaged else "A packaging/label image is included.")}]
        for photo in photos:
            parts.append({"inline_data": {"mime_type": getattr(getattr(photo, "file", photo), "content_type", "image/jpeg") or "image/jpeg", "data": photo.read().hex()}})
            photo.seek(0)
        # Gemini accepts base64 image data, not hexadecimal.
        import base64
        for index, photo in enumerate(photos, start=1):
            photo.seek(0)
            parts[index]["inline_data"]["data"] = base64.b64encode(photo.read()).decode()
            photo.seek(0)
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_VISION_MODEL}:generateContent?key={settings.GEMINI_API_KEY}",
            json={"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0}},
            timeout=settings.FOOD_VERIFICATION_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        if result.get("decision") not in {"approve", "reject", "review"}:
            raise ValueError("AI returned an unsupported verification decision.")
        result["confidence"] = max(0, min(100, int(result.get("confidence", 0))))
        result["summary"] = str(result.get("summary", "Visual screening completed."))[:1000]
        result["risk_flags"] = [str(flag)[:100] for flag in result.get("risk_flags", [])][:10]
        return result
