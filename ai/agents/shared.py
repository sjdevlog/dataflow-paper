import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

# 사용할 수 있는 모델은 계정마다 다름 → .env 의 GEMINI_MODEL 로 교체 가능
# gemini-flash-latest: 현재 키에서 쓸 수 있는 최신 Flash 모델을 가리키는 이름
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def get_llm():
    # timeout·재시도 횟수를 제한해서, 모델 이름이 틀리거나 한도 초과일 때
    # 조용히 멈추지 않고 바로 에러가 나도록 한다
    return init_chat_model(
        f"google_genai:{GEMINI_MODEL}",
        api_key=os.getenv("GOOGLE_API_KEY"),
        timeout=90,
        max_retries=2,
    )
