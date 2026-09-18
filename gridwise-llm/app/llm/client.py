import asyncio, json, logging
import httpx
from pydantic import ValidationError
from .models import RawInterpretationBatch
from .prompts import SYSTEM_PROMPT, build_user_prompt
from app.config import settings

log = logging.getLogger(__name__)

class LLMError(RuntimeError):
    pass

class LLMClient:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
        self._sem = asyncio.Semaphore(8)

    async def close(self):
        await self._client.aclose()

    async def interpret(self, notes, hours) -> RawInterpretationBatch:
        if settings.llm_provider == "mock":
            raise LLMError("mock provider is only available through injected test clients")
        if not settings.llm_api_key:
            raise LLMError("LLM provider is not configured")
        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.llm_model,
            "temperature": 0,
            "messages": [
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":build_user_prompt(notes, hours)}
            ],
            "response_format": {
                "type":"json_schema",
                "json_schema":{
                    "name":"gridwise_interpretation",
                    "strict":True,
                    "schema":{
                        "type":"object","additionalProperties":False,
                        "properties":{"interpretations":{
                            "type":"array","items":{
                                "type":"object","additionalProperties":False,
                                "properties":{
                                    "note_index":{"type":"integer"},
                                    "applies":{"type":"boolean"},
                                    "directive_type":{"type":"string","enum":[
                                        "solar_reduction","minimum_battery_reserve",
                                        "no_charge_window","no_discharge_window",
                                        "max_grid_window","no_op"]},
                                    "structured_adjustment":{"type":["object","null"]},
                                    "explanation":{"type":"string"}
                                },
                                "required":["note_index","applies","directive_type","structured_adjustment","explanation"]
                            }
                        }},
                        "required":["interpretations"]
                    }
                }
            }
        }
        last = None
        async with self._sem:
            for attempt in range(settings.llm_max_retries + 1):
                try:
                    r = await self._client.post(url, headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type":"application/json",
                    }, json=payload)
                    r.raise_for_status()
                    body = r.json()
                    content = body["choices"][0]["message"]["content"]
                    if isinstance(content, list):
                        content = "".join(x.get("text","") for x in content if isinstance(x,dict))
                    parsed = json.loads(content)
                    return RawInterpretationBatch.model_validate(parsed)
                except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValidationError, ValueError) as e:
                    last = e
                    if attempt < settings.llm_max_retries:
                        await asyncio.sleep(0.15 * (attempt + 1))
        raise LLMError(f"LLM interpretation failed: {type(last).__name__ if last else 'unknown'}")
