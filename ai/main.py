from deepagents import create_deep_agent
from dotenv import load_dotenv
from agents.shared import get_llm
from tools.hours import get_place_info
from tools.search import search_places
from tools.event import search_events
from tools.logger import new_session, end_session
import sys
load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')
llm = get_llm()
agent = create_deep_agent(
    model=llm, 
    tools=[search_places, get_place_info,search_events],
    system_prompt="당신은 데이트 코스 추천 AI입니다. "
    )

session_id = new_session()
print(f"[session] {session_id}")

try:
    result = agent.invoke({
        "messages": [{"role": "user", "content": " 26년 5월 20일 서울에서 할만한거"}]
    })
    end_session("success")
    print(result)
except Exception as e:
    end_session("failed", note=str(e))
    raise
