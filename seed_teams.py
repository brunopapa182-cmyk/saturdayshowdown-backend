import json
from sqlalchemy.orm import Session
from nhl_backend.database import SessionLocal
from nhl_backend.models_db import Team

def seed_teams():
    db: Session = SessionLocal()

    with open("nhl_teams.json", "r") as f:
        teams = json.load(f)

    for t in teams:
        team = Team(
            id=t["id"],
            name=t["name"],
            abbreviation=t["abbr"]
        )
        db.add(team)

    db.commit()
    db.close()

if __name__ == "__main__":
    seed_teams()
    print("Teams seeded successfully")
