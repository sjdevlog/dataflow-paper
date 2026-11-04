import os
from langchain.chat_models import init_chat_model
from langchain_core.rate_limiters import InMemoryRateLimiter
from dotenv import load_dotenv

load_dotenv()

# 사용할 수 있는 모델은 계정마다 다름 → .env 의 GEMINI_MODEL 로 교체 가능
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# 무료 등급은 분당 요청 수 제한이 있음 (예: gemini-3-flash 무료 5회/분).
# 한도보다 조금 낮게 맞춰 429 오류를 피한다. 유료 키면 .env 에서 GEMINI_RPM 을 올리면 됨.
GEMINI_RPM = float(os.getenv("GEMINI_RPM", "4"))

# 모든 에이전트가 같은 제한을 공유하도록 모듈 단위로 하나만 만든다
_rate_limiter = InMemoryRateLimiter(
    requests_per_second=GEMINI_RPM / 60,
    check_every_n_seconds=0.5,
    max_bucket_size=1,
)


def get_llm():
    # timeout·재시도 횟수를 제한해서, 모델 이름이 틀리거나 한도 초과일 때
    # 조용히 멈추지 않고 바로 에러가 나도록 한다
    return init_chat_model(
        f"google_genai:{GEMINI_MODEL}",
        api_key=os.getenv("GOOGLE_API_KEY"),
        timeout=90,
        max_retries=2,
        rate_limiter=_rate_limiter,
    )
