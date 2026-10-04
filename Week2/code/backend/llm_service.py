from openai import AsyncOpenAI
import os, json

client = AsyncOpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url="https://api.deepseek.com"
)

async def analyze_symptoms(symptoms: str) -> dict:
    prompt = f"""Phân tích triệu chứng sau và trả về JSON với format:
{{"risks": [{{"condition": "...", "risk_level": "high/medium/low"}}],
  "triage": "emergency/urgent/general/specialist",
  "suggested_specialty": "Nội tổng hợp/Hô hấp/Nội tiết"}}

Triệu chứng: {symptoms}

Chỉ trả JSON, không giải thích thêm."""

    response = await client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}  
    )
    return json.loads(response.choices[0].message.content)