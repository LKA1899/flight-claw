import json
import os
from urllib import request
from urllib.error import URLError

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """你是一个个人旅行价格分析助手。
你只能基于用户提供的结构化机票价格数据进行分析。
不要编造不存在的航班、价格、日期或平台。
如果数据不完整，必须明确说明。
甩尾方案必须标记为高风险，不要默认推荐。
你的输出使用 Markdown，语言为中文，简洁但有判断力。"""


def llm_configured() -> bool:
    return bool(_api_key())


def _base_url() -> str:
    value = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_COMPATIBLE_BASE_URL") or ""
    return value.strip().rstrip("/") or "https://api.openai.com/v1"


def _api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_COMPATIBLE_API_KEY") or "").strip()


def _model() -> str:
    return (os.getenv("OPENAI_MODEL") or os.getenv("OPENAI_COMPATIBLE_MODEL") or "gpt-4o-mini").strip()


def chat_completion(messages: list[dict], temperature: float = 0.2, timeout: int = 60) -> dict:
    api_key = _api_key()
    if not api_key:
        return {"enabled": False, "content": None, "error": "OPENAI_API_KEY is not configured"}

    url = f"{_base_url()}/chat/completions"
    payload = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return {"enabled": True, "content": content, "error": None, "raw": body}
    except (URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        return {"enabled": True, "content": None, "error": str(exc)}


def generate_report_summary(structured_summary: dict) -> dict:
    return chat_completion(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "请根据以下结构化数据生成购票建议 Markdown 报告。"
                    "报告必须包括：今日总体结论、每条 Monitor 的推荐、最低价方案、综合最优方案、"
                    "稳妥方案、激进省钱方案、是否建议今天买、风险提醒、数据不完整说明。\n\n"
                    f"```json\n{json.dumps(structured_summary, ensure_ascii=False, indent=2)}\n```"
                ),
            },
        ]
    )
