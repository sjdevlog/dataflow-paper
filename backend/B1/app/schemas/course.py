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

# 장소 정보
class PlaceItem(BaseModel):
    name:      str
    category:  str
    region:    str
    time:      str
    price:     int
    is_open:   bool
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

# 코스 생성 응답
class CourseResponse(BaseModel):
    course_id:  str
    user_id:    str
    region:     str
    budget_max: int = 100000
    weather:    Optional[str] = None
    courses:    List[CourseItem]
