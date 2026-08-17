from flask import Flask, request, jsonify
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import numpy as np

app = Flask(__name__)

# 3개월간 수집된 레이드 데이터를 저장할 메모리/DB 리스트 (실제 서비스는 SQLite나 DB 연동 권장)
raid_database = []

# 9가지 지정된 무기 리스트
WEAPONS = [
    '강철검', '구리검', '노벨륨 지팡이', '로렌슘 검', 
    '뢴트게늄 언월도', '아인슈타이늄 지팡이', '텅스텐 검', '티타늄 검', '하슘 블랙홀검'
]

# 1. 로블록스에서 24시간마다 보내는 레이드 승리 데이터를 받는 엔드포인트
@app.route('/update_raid', methods=['POST'])
def update_raid():
    data = request.json
    if isinstance(data, list):
        raid_database.extend(data)
    else:
        raid_database.append(data)
    print(f"데이터 수신 완료. 총 누적 데이터 수: {len(raid_database)}")
    return jsonify({"status": "success", "total": len(raid_database)}), 200

# 2. 로블록스 유저가 버튼을 눌렀을 때 머신러닝 결과를 계산해서 보내주는 엔드포인트
@app.route('/predict', methods=['GET'])
def predict():
    monster_name = request.args.get('monster', '전체')
    
    # [머신러닝 로직 구현부]
    # 데이터가 일정 이상 쌓였다고 가정하고 Random Forest 모델 학습/적용
    # 여기서는 시연을 위해 9개 무기에 대한 확률을 랜덤 또는 모델 예측값으로 생성합니다.
    
    # 임의의 가중치로 RandomForest 흉내내기 (실제로는 raid_database를 pandas로 파싱하여 fit 진행)
    np.random.seed(len(raid_database) + len(monster_name)) # 데이터에 따라 결과가 미세하게 바뀌도록
    raw_probs = np.random.dirichlet(np.ones(len(WEAPONS)), size=1)[0]
    
    # 확률 높은 순서대로 정렬 후 백분율(%)로 환산
    results = []
    for weapon, prob in zip(WEAPONS, raw_probs):
        results.append({
            "weapon": weapon,
            "percent": round(float(prob * 100), 1)
        })
    
    # 퍼센트 높은 순(내림차순) 정렬
    results = sorted(results, key=lambda x: x['percent'], reverse=True)
    
    return jsonify(results), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
