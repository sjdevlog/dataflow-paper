import math
import os
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
KMA_API_KEY = os.getenv("KMA_API_KEY")

# 강수형태 코드
PTY_CODE = {
    0: "없음",
    1: "비",
    2: "비/눈",
    3: "눈",
    4: "소나기",
    5: "빗방울",
    6: "빗방울/눈날림",
    7: "눈날림",
}

# 하늘상태 코드 (단기예보용)
SKY_CODE = {
    1: "맑음",
    3: "구름많음",
    4: "흐림",
}

# 단기예보 발표시각 (하루 8회)
FORECAST_BASE_TIMES = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]


def latlon_to_grid(lat: float, lon: float) -> dict:
    """위경도 → 기상청 격자 좌표 변환"""
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43
    YO = 136

    DEGRAD = math.pi / 180.0

    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)

    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + XO + 0.5)
    ny = int(ro - ra * math.cos(theta) + YO + 0.5)

    return {"nx": nx, "ny": ny}


def _get_base_datetime():
    """현재 시각 기준 가장 가까운 단기예보 발표시각 계산"""
    now = datetime.now()
    current_time = now.strftime("%H%M")

    # 발표 후 API 반영까지 약 10분 소요
    adjusted = now - timedelta(minutes=10)
    adjusted_time = adjusted.strftime("%H%M")

    base_date = now.strftime("%Y%m%d")
    base_time = "2300"  # 기본값 (전날 23시)

    for bt in FORECAST_BASE_TIMES:
        if adjusted_time >= bt:
            base_time = bt

    # 자정~02:10 사이면 전날 2300 사용
    if adjusted_time < "0210":
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        base_time = "2300"

    return base_date, base_time


async def get_weather(lat: float, lon: float, region: str = "알 수 없음", target_date: str = None, target_time: str = None) -> dict:
    """단기예보 기반 날씨 조회 (현재 + 미래 날짜 가능)"""
    grid = latlon_to_grid(lat, lon)
    base_date, base_time = _get_base_datetime()

    # 목표 날짜/시간 설정 (없으면 현재)
    if not target_date:
        target_date = datetime.now().strftime("%Y%m%d")
    if not target_time:
        target_time = datetime.now().strftime("%H00")

    print(f"DEBUG: target_date={target_date}, target_time={target_time}")  # 이 줄 추가

    url = (
        f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        f"?serviceKey={KMA_API_KEY}"
        f"&numOfRows=300&pageNo=1&dataType=JSON"
        f"&base_date={base_date}&base_time={base_time}"
        f"&nx={grid['nx']}&ny={grid['ny']}"
    )

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=5.0)
            data = res.json()

        items = data["response"]["body"]["items"]["item"]

        # 목표 날짜+시간에 해당하는 데이터 추출
        result = {}
        for item in items:
            if item["fcstDate"] == target_date and item["fcstTime"] == target_time:
                result[item["category"]] = item["fcstValue"]

        # 정확한 시간 못 찾으면 해당 날짜 첫 데이터 사용
        if not result:
            for item in items:
                if item["fcstDate"] == target_date:
                    result.setdefault(item["category"], item["fcstValue"])

        # 단기예보 범위(약 3일) 밖 → 기본값(0°C·맑음)을 실제 예보처럼 돌려주지 않도록 실패 처리
        if not result:
            raise ValueError(f"{target_date} 예보 없음 (단기예보 범위 밖)")

        temp     = float(result.get("TMP", 0))     # 기온
        pcp_raw = result.get("PCP", "0")
        pcp_clean = pcp_raw.replace("강수없음", "0").replace("mm 미만", "").replace("mm", "").strip()
        try:
            rain = float(pcp_clean)
        except ValueError:
            rain = 0.0
        humidity = float(result.get("REH", 0))     # 습도
        wind     = float(result.get("WSD", 0))     # 풍속
        pty      = int(float(result.get("PTY", 0)))  # 강수형태
        sky      = int(float(result.get("SKY", 1)))  # 하늘상태
        pop      = int(float(result.get("POP", 0)))  # 강수확률

        pty_desc = PTY_CODE.get(pty, "알 수 없음")
        sky_desc = SKY_CODE.get(sky, "알 수 없음")

        # 강수 없으면 하늘상태로 표시
        description = pty_desc if pty > 0 else sky_desc

        # TODO: 빗방울(5), 눈날림(7) 등 약한 강수는 야외 가능하도록 세분화 필요
        is_outdoor_ok = pty == 0

        return {
            "region":        region,
            "temperature":   temp,
            "rainfall":      rain,
            "humidity":      humidity,
            "wind_speed":    wind,
            "pty_code":      pty,
            "sky_code":      sky,
            "sky_desc":      sky_desc,
            "pop":           pop,
            "description":   description,
            "is_outdoor_ok": is_outdoor_ok,
            "forecast_date": target_date,
            "forecast_time": target_time,
        }

    except Exception as e:
        return {
            "region":        region,
            "temperature":   None,
            "rainfall":      None,
            "humidity":      None,
            "wind_speed":    None,
            "pty_code":      None,
            "sky_code":      None,
            "sky_desc":      None,
            "pop":           None,
            "description":   "날씨 정보 없음",
            "is_outdoor_ok": True,
            "forecast_date": target_date,
            "forecast_time": target_time,
            "error":         str(e),
        }