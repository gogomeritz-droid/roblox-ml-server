from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import time

app = FastAPI()

# 레이드 기록을 저장할 리스트 (timestamp 포함)
raid_history = []

class RaidData(BaseModel):
    monster: str
    weapon: str
    timestamp: float = None  # 시간 정보 추가 (없으면 서버 시간 자동 기록)

@app.post("/update_raid")
def update_raid(data: RaidData):
    # 시간이 안 넘어왔다면 현재 시간(타임스탬프) 기록
    current_time = data.timestamp if data.timestamp else time.time()
    
    raid_history.append({
        "monster": data.monster,
        "weapon": data.weapon,
        "timestamp": current_time
    })
    return {"status": "success"}

@app.get("/get_monster_stats/{monster_name}")
def get_monster_stats(monster_name: str):
    # 🕒 현재 시간과 3개월(90일 = 90 * 24 * 60 * 60 초) 전 시간 계산
    now = time.time()
    three_months_ago = now - (90 * 24 * 60 * 60)
    
    # 1. [핵심] 해당 몬스터이면서, 동시에 최근 3개월 이내에 기록된 데이터만 필터링!
    filtered = [
        item for item in raid_history 
        if item["monster"] == monster_name and item["timestamp"] >= three_months_ago
    ]
    
    if not filtered:
        return {"weapons": []}
    
    # 2. Pandas를 이용해 무기별 사용 횟수 집계
    df = pd.DataFrame(filtered)
    counts = df["weapon"].value_counts().reset_index()
    counts.columns = ["weapon", "count"]
    
    # 3. 백분율 계산 및 정렬
    total = counts["count"].sum()
    counts["percentage"] = (counts["count"] / total) * 100
    counts = counts.sort_values(by="percentage", ascending=False)
    
    return {"weapons": counts.to_dict(orient="records")}
