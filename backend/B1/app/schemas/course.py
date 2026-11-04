from pydantic import BaseModel
from typing import Optional, List, Literal

# 코스 생성 요청
class CourseRequest(BaseModel):
    user_id:       str
    region:        str
    lat:           float
    lon:           float
    budget_min:    int = 0
    budget_max:    int = 100000
    weather:       Optional[str] = None
    date:          Optional[str] = None   # YYYY-MM-DD
    temp:          Optional[float] = None
    tags_a:        List[str] = []
    tags_b:        List[str] = []
    tags_m:        List[str] = []         # deprecated: tags_a 사용
    tags_f:        List[str] = []         # deprecated: tags_b 사용
    natural_input: Optional[str] = None
    selected_event: Optional[dict] = None  # 사용자가 고른 메인 이벤트 (없으면 Pipeline 1 첫 번째)
    no_event:      bool = False            # 주변에 이벤트 장소가 없어 이벤트 없이 짜는 경우

# 장소 정보
class PlaceItem(BaseModel):
    name:      str
    category:  str
    region:    str
    time:      str
    price:     int
    is_open:   bool
    open_status: Optional[Literal["open", "closed", "unknown"]] = None  # check ② 판정
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    walk_minutes_to_next: Optional[int] = None
    car_minutes_to_next: Optional[int] = None
    satisfaction_a: Optional[int] = None
    satisfaction_b: Optional[int] = None

# 코스 하나
class CourseItem(BaseModel):
    title:       str
    total_price: int
    places:      List[PlaceItem]
    source:      Literal["ai", "b2"] = "b2"
    avg_satisfaction_a: Optional[float] = None
    avg_satisfaction_b: Optional[float] = None
    fairness_gap:       Optional[float] = None
    violations:         Optional[int] = None   # 영업시간 위반 장소 수 V(C)

# 코스 생성 응답
class CourseResponse(BaseModel):
    course_id:  str
    user_id:    str
    region:     str
    budget_max: int = 100000
    weather:    Optional[str] = None
    courses:    List[CourseItem]


# 메인 이벤트 추천 요청 / 응답
class EventRequest(BaseModel):
    region:        str
    lat:           float
    lon:           float
    date:          Optional[str] = None
    tags_a:        List[str] = []
    tags_b:        List[str] = []
    natural_input: Optional[str] = None
    exclude:       List[str] = []      # '더 보기'에서 이미 보여준 이벤트 이름
    more:          bool = False        # True면 AI 없이 카카오 검색으로 MORE_SIZE개 추가

class EventItem(BaseModel):
    name:      str
    category:  str
    address:   str = ""
    place_url: str = ""
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    reason:    str = ""
    source:    Literal["ai", "kakao"] = "kakao"

class EventResponse(BaseModel):
    events:  List[EventItem]
    source:  Literal["ai", "kakao", "ai+kakao", "none"]
    message: str = ""


# '다른 장소 추천' 요청 / 응답
class LatLon(BaseModel):
    lat: float
    lon: float

class AlternativeRequest(BaseModel):
    name:     str
    category: str
    lat:      float
    lon:      float
    time:     str = ""
    date:     Optional[str] = None
    tags_a:   List[str] = []
    tags_b:   List[str] = []
    exclude:  List[str] = []          # 코스에 이미 있는 장소 이름
    prev:     Optional[LatLon] = None # 앞 장소 좌표 (이동시간 재계산용)
    next:     Optional[LatLon] = None # 뒤 장소 좌표

class AlternativeItem(BaseModel):
    name:           str
    category:       str
    address:        str = ""
    place_url:      str = ""
    latitude:       float
    longitude:      float
    open_status:    Literal["open", "closed", "unknown"] = "unknown"
    satisfaction_a: int
    satisfaction_b: int
    objective:      float
    walk_from_prev: Optional[int] = None
    walk_to_next:   Optional[int] = None

class AlternativeResponse(BaseModel):
    alternatives: List[AlternativeItem]
    message:      str = ""
