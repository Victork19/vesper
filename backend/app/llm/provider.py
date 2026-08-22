import json, os
from typing import Any

SYSTEM='''You are Vesper, a long-horizon autonomous decision agent. Use persisted scars as hard operational lessons. Never ignore an active scar. Return only JSON with keys: action, rationale, risk_score, cited_scars, outcome.'''

class LLMProvider:
    def __init__(self):
        self.groq_key=os.getenv('GROQ_API_KEY'); self.enabled=bool(self.groq_key)
    def complete(self,situation:str,scars:list[dict[str,Any]])->dict[str,Any]|None:
        if not self.groq_key:return None
        try:
            from groq import Groq
            prompt=json.dumps({'situation':situation,'active_scars':scars},ensure_ascii=False)
            response=Groq(api_key=self.groq_key).chat.completions.create(model=os.getenv('GROQ_MODEL','llama-3.3-70b-versatile'),temperature=.35,response_format={'type':'json_object'},messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}])
            return json.loads(response.choices[0].message.content)
        except Exception:
            return None
