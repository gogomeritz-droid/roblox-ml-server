from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

app = FastAPI()

raid_history = []

class RaidData(BaseModel):
    monster: str
    weapon: str

@app.post("/update_raid")
def update_raid(data: RaidData):
    raid_history.append({"monster": data.monster, "weapon": data.weapon})
    return {"status": "success"}

@app.get("/get_monster_stats/{monster_name}")
def get_monster_stats(monster_name: str):
    filtered = [item for item in raid_history if item["monster"] == monster_name]
    if not filtered:
        return {"weapons": []}
    
    df = pd.DataFrame(filtered)
    counts = df["weapon"].value_counts().reset_index()
    counts.columns = ["weapon", "count"]
    
    total = counts["count"].sum()
    counts["percentage"] = (counts["count"] / total) * 100
    counts = counts.sort_values(by="percentage", ascending=False)
    
    return {"weapons": counts.to_dict(orient="records")}