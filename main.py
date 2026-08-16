from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
import numpy as np
import time
import threading
from sklearn.ensemble import RandomForestClassifier

app = FastAPI()

# 1. 9가지 지정된 무기 리스트 정의
VALID_WEAPONS = [
    "하슘검",
    "로렌슘검",
    "노벨륨지팡이",
    "아인슈타이늄지팡이",
    "니호늄검",
    "뢴트겐언월도",
    "티타늄검",
    "텅스텐검",
    "강철검"
]

# 2. 8가지 지정된 레이드 몬스터 리스트 정의
VALID_MONSTERS = [
    "물질의 수호자 로봇(입자 가속기)",
    "미노타우로스(입자 가속기)",
    "쌍둥이 싸이클롭스 (입자 가속기)",
    "미노타우로스 로봇 (잃어버린 도시)",
    "싸이클롭스 (잃어버린 도시)",
    "사막 골렘(신들의 사막)",
    "아이스 골렘(얼어붙은 세계)",
    "존비 골렘(연금술사의 숲)"
]

# 전체 레이드 기록 저장소
raid_history = []

# 머신러닝 예측 결과가 캐싱되는 저장소 (클라이언트 요청 즉시 응답용)
cached_ml_results = {}

class RaidData(BaseModel):
    monster: str
    weapon: str
    timestamp: float = None  # 타임스탬프 (없으면 서버 시간 자동 기록)

@app.post("/update_raid")
def update_raid(data: RaidData):
    """
    [데이터 수집 엔드포인트]
    로블록스에서 레이드 종료 시 전송된 데이터를 누적 저장합니다.
    """
    # 유효성 검사 (선택 사항이지만 안전성을 위해 추가)
    if data.monster not in VALID_MONSTERS:
        raise HTTPException(status_code=400, detail="유효하지 않은 몬스터 이름입니다.")
    if data.weapon not in VALID_WEAPONS:
        raise HTTPException(status_code=400, detail="유효하지 않은 무기 이름입니다.")

    current_time = data.timestamp if data.timestamp else time.time()
    
    raid_history.append({
        "monster": data.monster,
        "weapon": data.weapon,
        "timestamp": current_time
    })
    return {"status": "success", "message": "데이터가 정상적으로 수집되었습니다."}

def run_random_forest_ml_analysis():
    """
    [24시간 주기 머신러닝 분석 백그라운드 스레드]
    - 최근 3개월 데이터만 필터링합니다.
    - 각 몬스터별로 RandomForestClassifier 모델을 학습시킵니다.
    - 모델의 예측 확률(predict_proba)을 추출하여 9개 무기의 백분율 통계를 산출합니다.
    """
    global cached_ml_results
    while True:
        try:
            now = time.time()
            three_months_ago = now - (90 * 24 * 60 * 60) # 최근 3개월 (90일)
            
            new_cache = {}
            
            for monster in VALID_MONSTERS:
                # 1. 최근 3개월 이내 + 해당 몬스터 데이터 필터링
                filtered = [
                    item for item in raid_history 
                    if item["monster"] == monster and item["timestamp"] >= three_months_ago
                ]
                
                stats_dict = {w: 0.0 for w in VALID_WEAPONS}
                
                if len(filtered) >= 5: # 학습에 필요한 최소 데이터가 있을 경우 머신러닝 구동
                    df = pd.DataFrame(filtered)
                    
                    # 피처 엔지니어링: timestamp를 정규화하여 학습 특성(X)으로 사용
                    min_t = df["timestamp"].min()
                    df["relative_time"] = df["timestamp"] - min_t
                    
                    X = df[["relative_time"]]
                    y = df["weapon"]
                    
                    # RandomForest 모델 초기화 및 학습 (랜덤포레스트 적용)
                    model = RandomForestClassifier(n_estimators=50, random_state=42)
                    model.fit(X, y)
                    
                    # 현재 시점을 기준으로 9개 무기에 대한 선택 확률 예측
                    latest_time = df["relative_time"].max()
                    X_test = pd.DataFrame({"relative_time": [latest_time]})
                    
                    if hasattr(model, "predict_proba"):
                        probs = model.predict_proba(X_test)[0]
                        classes = model.classes_
                        
                        # 모델이 예측한 확률을 백분율로 매핑
                        prob_map = {cls: prob * 100 for cls, prob in zip(classes, probs)}
                        for w in VALID_WEAPONS:
                            stats_dict[w] = float(prob_map.get(w, 0.0))
                elif len(filtered) > 0:
                    # 데이터가 적을 때는 단순 백분율 통계로 대체 (콜드스타트 방지)
                    df = pd.DataFrame(filtered)
                    counts = df["weapon"].value_counts().to_dict()
                    total = sum(counts.values())
                    for w in VALID_WEAPONS:
                        stats_dict[w] = (counts.get(w, 0) / total) * 100

                # 2. 결과 정렬 (백분율이 가장 큰 순서대로 내림차순 정렬)
                weapon_ranking = []
                for w in VALID_WEAPONS:
                    weapon_ranking.append({
                        "weapon": w,
                        "percentage": round(stats_dict[w], 1) # 소수점 첫째 자리
                    })
                
                weapon_ranking = sorted(weapon_ranking, key=lambda x: x["percentage"], reverse=True)
                new_cache[monster] = weapon_ranking
            
            # 캐시 업데이트
            cached_ml_results = new_cache
            
        except Exception as e:
            print(f"Random Forest ML Error: {e}")
            
        # 24시간(86400초) 대기 후 재학습 (테스트 시에는 시간을 줄여서 확인 가능)
        time.sleep(86400)

@app.on_event("startup")
def startup_event():
    """서버 시작 시 24시간 주기 머신러닝 스레드 백그라운드 실행"""
    thread = threading.Thread(target=run_random_forest_ml_analysis, daemon=True)
    thread.start()

@app.get("/get_raid_stats")
def get_raid_stats(monster: str = Query(..., description="조회할 몬스터 이름")):
    """
    [로블록스 연동용 GET 엔드포인트]
    로블록스에서 `/get_raid_stats?monster=보스이름` 형식으로 요청하면 
    머신러닝이 분석한 9개 무기 통계 백분율 결과를 즉시 반환합니다.
    """
    if monster not in VALID_MONSTERS:
        raise HTTPException(status_code=400, detail="존재하지 않는 몬스터입니다.")

    if monster in cached_ml_results:
        return {
            "monster": monster,
            "weapons": cached_ml_results[monster]
        }
    
    # 데이터가 아직 없는 초기 상태인 경우 0%로 9개 무기 반환
    default_ranking = [{"weapon": w, "percentage": 0.0} for w in VALID_WEAPONS]
    return {
        "monster": monster,
        "weapons": default_ranking
    }
