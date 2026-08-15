from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

# FastAPI 앱 생성 (서버 시작점)
app = FastAPI()

# 🧠 레이드 데이터를 임시로 저장할 메모리 리스트 (서버가 켜져 있는 동안 유지됨)
raid_history = []

# 로블록스에서 보낼 데이터의 형식을 정의하는 클래스 (데이터 검증용)
class RaidData(BaseModel):
    monster: str  # 몬스터 이름 (예: "ZombieGolem")
    weapon: str   # 무기 이름 (예: "하슘 암흑 검")

# [API 1] 로블록스가 24시간마다 데이터를 보낼 때(POST) 호출되는 주소
@app.post("/update_raid")
def update_raid(data: RaidData):
    # 받은 데이터를 리스트에 추가 (누적 저장)
    raid_history.append({"monster": data.monster, "weapon": data.weapon})
    return {"status": "success", "message": "데이터 저장 완료"}

# [API 2] 로블록스 유저가 인벤토리를 열어 특정 몬스터의 통계를 요청할 때(GET) 호출되는 주소
@app.get("/get_monster_stats/{monster_name}")
def get_monster_stats(monster_name: str):
    # 1. 요청한 몬스터 이름과 일치하는 데이터만 골라내기 (필터링)
    filtered = [item for item in raid_history if item["monster"] == monster_name]
    
    # 데이터가 아예 없다면 빈 리스트 반환
    if not filtered:
        return {"weapons": []}
    
    # 2. Pandas를 이용해 무기별 등장 횟수(인기 순위) 집계
    df = pd.DataFrame(filtered)
    counts = df["weapon"].value_counts().reset_index()
    counts.columns = ["weapon", "count"]
    
    # 3. 전체 합계 기준으로 백분율(%) 계산
    total = counts["count"].sum()
    counts["percentage"] = (counts["count"] / total) * 100
    
    # 4. 퍼센트가 높은 순서대로(내림차순) 정렬
    counts = counts.sort_values(by="percentage", ascending=False)
    
    # 5. 로블록스가 읽기 편한 딕셔너리 형태로 변환해서 반환
    return {"weapons": counts.to_dict(orient="records")}
