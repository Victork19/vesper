import json, os
from typing import Any

SYSTEM = '''You are Vesper, a long-horizon autonomous agent. Your personality, risk tolerance, and decision boundaries are permanently shaped by operational scars stored in Sibyl Memory.
Never ignore an active scar. If a scar influences your decision, cite its exact ID and lesson. Prefer refusal over repeating a known failure.
Return only JSON with keys: action, rationale, risk_score, cited_scars, outcome.'''

class LLMProvider:
    def __init__(self):
        self.groq_key=os.getenv('GROQ_API_KEY'); self.gemini_key=os.getenv('GEMINI_API_KEY')
    def complete(self, situation: str, scars: list[dict[str,Any]]) -> dict[str,Any] | None:
        prompt=json.dumps({'situation':situation,'active_scars':scars}, ensure_ascii=False)
        if self.groq_key:
            try:
                from groq import Groq
                r=Groq(api_key=self.groq_key).chat.completions.create(model=os.getenv('GROQ_MODEL','llama-3.3-70b-versatile'),temperature=.35,response_format={'type':'json_object'},messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}])
                return json.loads(r.choices[0].message.content)
            except Exception:
                pass
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                r=genai.GenerativeModel(os.getenv('GEMINI_MODEL','gemini-2.0-flash')).generate_content(SYSTEM+'\n'+prompt, generation_config={'temperature':.35,'response_mime_type':'application/json'})
                return json.loads(r.text)
            except Exception:
                pass
        return None
