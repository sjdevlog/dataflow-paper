import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

# gemini-2.5-flash 는 신규 사용자에게 더 이상 제공되지 않음 → .env 의 GEMINI_MODEL 로 교체 가능
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def get_llm():
    return init_chat_model(
        f"google_genai:{GEMINI_MODEL}",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )
