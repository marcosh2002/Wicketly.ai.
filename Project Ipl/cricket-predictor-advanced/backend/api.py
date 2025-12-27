# ...existing code...
from fastapi import FastAPI, Query, Request, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import joblib
import pandas as pd
import numpy as np
import os
import random
import json
import uuid
import hashlib
import csv
import requests
import warnings
from datetime import datetime
from fastapi import HTTPException
import pvp_utils
from sklearn.exceptions import InconsistentVersionWarning
from unified_db import (
    init_db, get_db, User, create_user, get_user_by_username,
    authenticate_user, deduct_tokens, add_tokens, hash_password, verify_password
)

# Team name mapping for user-friendly input
TEAM_NAME_MAP = {
    "CSK": "CHENNAI SUPER KINGS",
    "CHENNAI SUPER KINGS": "CHENNAI SUPER KINGS",
    "MI": "MUMBAI INDIANS",
    "MUMBAI INDIANS": "MUMBAI INDIANS",
    "RCB": "ROYAL CHALLENGERS BANGALORE",
    "ROYAL CHALLENGERS BANGALORE": "ROYAL CHALLENGERS BANGALORE",
    "ROYAL CHALLENGERS BENGALURU": "ROYAL CHALLENGERS BANGALORE",
    "KKR": "KOLKATA KNIGHT RIDERS",
    "KOLKATA KNIGHT RIDERS": "KOLKATA KNIGHT RIDERS",
    "SRH": "SUNRISERS HYDERABAD",
    "SUNRISERS HYDERABAD": "SUNRISERS HYDERABAD",
    "DC": "DELHI CAPITALS",
    "DELHI CAPITALS": "DELHI CAPITALS",
    "DD": "DELHI DAREDEVILS",
    "DELHI DAREDEVILS": "DELHI CAPITALS",
    "PBKS": "PUNJAB KINGS",
    "PUNJAB KINGS": "PUNJAB KINGS",
    "KXIP": "PUNJAB KINGS",
    "KINGS XI PUNJAB": "PUNJAB KINGS",
    "RR": "RAJASTHAN ROYALS",
    "RAJASTHAN ROYALS": "RAJASTHAN ROYALS",
    "GT": "GUJARAT TITANS",
    "GUJARAT TITANS": "GUJARAT TITANS",
    "LSG": "LUCKNOW SUPER GIANTS",
    "LUCKNOW SUPER GIANTS": "LUCKNOW SUPER GIANTS",
}

# IPL 2025 Teams Data
TEAMS_2025 = {
    "CSK": {
        "name": "CSK",
        "fullName": "CHENNAI SUPER KINGS",
        "captain": "Ruturaj Gaikwad",
        "coach": "Stephen Fleming",
        "titles": 5,
        "home": "Chennai",
        "topScorer": "Ruturaj Gaikwad",
        "topBowler": "Matheesha Pathirana",
        "founded": 2008,
    },
    "MI": {
        "name": "MI",
        "fullName": "MUMBAI INDIANS",
        "captain": "Hardik Pandya",
        "coach": "Mark Boucher",
        "titles": 5,
        "home": "Mumbai",
        "topScorer": "Suryakumar Yadav",
        "topBowler": "Jasprit Bumrah",
        "founded": 2008,
    },
    "RCB": {
        "name": "RCB",
        "fullName": "ROYAL CHALLENGERS BANGALORE",
        "captain": "Faf du Plessis",
        "coach": "Andy Flower",
        "titles": 1,
        "home": "Bangalore",
        "topScorer": "Virat Kohli",
        "topBowler": "Mohammed Siraj",
        "founded": 2008,
    },
    "KKR": {
        "name": "KKR",
        "fullName": "KOLKATA KNIGHT RIDERS",
        "captain": "Shreyas Iyer",
        "coach": "Chandrakant Pandit",
        "titles": 3,
        "home": "Kolkata",
        "topScorer": "Sunil Narine",
        "topBowler": "Varun Chakravarthy",
        "founded": 2008,
    },
    "PBKS": {
        "name": "PBKS",
        "fullName": "PUNJAB KINGS",
        "captain": "Shikhar Dhawan",
        "coach": "Trevor Bayliss",
        "titles": 0,
        "home": "Mohali",
        "topScorer": "Shikhar Dhawan",
        "topBowler": "Arshdeep Singh",
        "founded": 2008,
    },
    "RR": {
        "name": "RR",
        "fullName": "RAJASTHAN ROYALS",
        "captain": "Sanju Samson",
        "coach": "Kumar Sangakkara",
        "titles": 1,
        "home": "Jaipur",
        "topScorer": "Yashasvi Jaiswal",
        "topBowler": "Trent Boult",
        "founded": 2008,
    },
    "GT": {
        "name": "GT",
        "fullName": "GUJARAT TITANS",
        "captain": "Shubman Gill",
        "coach": "Ashish Nehra",
        "titles": 1,
        "home": "Ahmedabad",
        "topScorer": "Shubman Gill",
        "topBowler": "Mohit Sharma",
        "founded": 2022,
    },
    "LSG": {
        "name": "LSG",
        "fullName": "LUCKNOW SUPER GIANTS",
        "captain": "KL Rahul",
        "coach": "Justin Langer",
        "titles": 0,
        "home": "Lucknow",
        "topScorer": "KL Rahul",
        "topBowler": "Naveen-ul-Haq",
        "founded": 2022,
    },
    "DC": {
        "name": "DC",
        "fullName": "DELHI CAPITALS",
        "captain": "Rishabh Pant",
        "coach": "Ricky Ponting",
        "titles": 0,
        "home": "Delhi",
        "topScorer": "Rishabh Pant",
        "topBowler": "Kuldeep Yadav",
        "founded": 2008,
    },
# ...existing code...
    "SRH": {
        "name": "SRH",
        "fullName": "SUNRISERS HYDERABAD",
        "captain": "Pat Cummins",
        "coach": "Daniel Vettori",
        "titles": 1,
        "home": "Hyderabad",
        "topScorer": "Abhishek Sharma",
        "topBowler": "T Natarajan",
        "founded": 2013,
    },
}

# Create a player-to-team mapping from the TEAMS_2025 data
PLAYER_TO_TEAM = {}
for team_code, team_info in TEAMS_2025.items():
    PLAYER_TO_TEAM[team_info["captain"]] = team_code
    PLAYER_TO_TEAM[team_info["topScorer"]] = team_code
    PLAYER_TO_TEAM[team_info["topBowler"]] = team_code

# IPL 2025 Venues
VENUES_2025 = [
    "M. A. Chidambaram Stadium, Chennai",
    "Wankhede Stadium, Mumbai",
    "M. Chinnaswamy Stadium, Bangalore",
    "Eden Gardens, Kolkata",
    "Punjab Cricket Association Stadium, Mohali",
    "Rajasthan Cricket Association Stadium, Jaipur",
    "Narendra Modi Stadium, Ahmedabad",
    "BRSABVE Cricket Ground, Lucknow",
    "Arun Jaitley Stadium, Delhi",
    "Rajiv Gandhi International Cricket Stadium, Hyderabad",
]

# Request Models
class PredictionRequest(BaseModel):
    team1: str
    team2: str
    venue: str
    weather: str
    runsTeam1: int
    runsTeam2: int
    wicketsTeam1: int
    wicketsTeam2: int
    username: Optional[str] = None

class WicketPredictionRequest(BaseModel):
    team1: str
    team2: str
    overs: int
    wicketsTeam1: Optional[int] = 3
    wicketsTeam2: Optional[int] = 3

app = FastAPI(title="IPL Predictor API 2025", version="2.0")

# Initialize unified database
init_db()

# Enable CORS for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model and encoders (if they exist)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=InconsistentVersionWarning)

try:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
    if os.path.exists(MODEL_PATH):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model_bundle = joblib.load(MODEL_PATH)
            model = model_bundle["model"]
            team_encoder = model_bundle["team_encoder"]
            winner_encoder = model_bundle["winner_encoder"]
        print("✓ Model loaded successfully (version warnings suppressed)")
    else:
        model = None
        print("⚠ Model file not found - using fallback predictions")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    model = None

def normalize_team_name(name):
    """Normalize team name to standard format"""
    key = name.strip().upper()
    if key in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[key]
    key = key.replace("THE ", "")
    if key in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[key]
    for k in TEAM_NAME_MAP:
        if key == k.upper():
            return TEAM_NAME_MAP[k]
    return key

def get_team_short_name(full_name):
    """Convert full team name to short name"""
    for short, full in TEAM_NAME_MAP.items():
        if full == full_name and len(short) <= 4:
            return short
    return full_name

def predict_match(team1: str, team2: str, venue: str, weather: str, runsTeam1: int, runsTeam2: int, wicketsTeam1: int, wicketsTeam2: int):
    """Predict match winner based on runs, wickets, venue, and weather"""
    
    # Base score calculation from runs
    team1_score = runsTeam1 * 0.6
    team2_score = runsTeam2 * 0.6
    
    # Adjust based on wickets (less wickets = higher score)
    team1_score += (10 - wicketsTeam1) * 5
    team2_score += (10 - wicketsTeam2) * 5
    
    # Adjust based on weather
    if weather.lower() == "rainy":
        team1_score -= 5
        team2_score -= 5
    elif weather.lower() == "hot":
        team1_score += 3
        team2_score += 3
    elif weather.lower() == "sunny":
        team1_score += 2
        team2_score += 2
    
    # Home advantage
    home_teams = {
        "CHENNAI SUPER KINGS": "Chennai",
        "MUMBAI INDIANS": "Mumbai",
        "ROYAL CHALLENGERS BANGALORE": "Bangalore",
        "KOLKATA KNIGHT RIDERS": "Kolkata",
        "PUNJAB KINGS": "Mohali",
        "RAJASTHAN ROYALS": "Jaipur",
        "GUJARAT TITANS": "Ahmedabad",
        "LUCKNOW SUPER GIANTS": "Lucknow",
        "DELHI CAPITALS": "Delhi",
        "SUNRISERS HYDERABAD": "Hyderabad",
    }
    
    team1_norm = normalize_team_name(team1)
    team2_norm = normalize_team_name(team2)
    
    if team1_norm in home_teams and home_teams[team1_norm] in venue:
        team1_score += 10
    if team2_norm in home_teams and home_teams[team2_norm] in venue:
        team2_score += 10
    
    # Determine winner
    winner = team1 if team1_score > team2_score else team2
    total_score = team1_score + team2_score
    winning_probability = max(team1_score, team2_score) / total_score * 100 if total_score > 0 else 50.0
    
    # Confidence level
    score_diff = abs(team1_score - team2_score)
    if score_diff > 15:
        confidence = "High"
    elif score_diff > 8:
        confidence = "Medium"
    else:
        confidence = "Low"
    
    return {
        "team1": team1,
        "team2": team2,
        "predicted_winner": winner,
        "team1_score": round(team1_score, 2),
        "team2_score": round(team2_score, 2),
        "winning_probability": round(winning_probability, 2),
        "confidence": confidence
    }

def predict_wickets(team1: str, team2: str, overs: int, wicketsTeam1: int = 3, wicketsTeam2: int = 3):
    """Predict wickets and match statistics"""
    
    base_wickets = wicketsTeam1 + wicketsTeam2
    
    if overs <= 6:
        base_wickets = min(base_wickets, 4)
    elif overs <= 12:
        base_wickets = min(base_wickets, 6)
    else:
        base_wickets = min(base_wickets, 10)
    
    return {
        "team1": team1,
        "team2": team2,
        "overs": overs,
        "predicted_wickets": base_wickets,
        "predicted_boundaries": random.randint(8, 15),
        "predicted_sixes": random.randint(2, 8),
        "predicted_extras": random.randint(2, 8)
    }

# ==================== ROOT ENDPOINT ====================
@app.get("/")
def read_root():
    return {
        "message": "Welcome to IPL Predictor API 2025!",
        "version": "2.0",
        "features": [
            "Match Prediction",
            "Wicket Prediction",
            "Team Information",
            "Player Data",
            "Match History"
        ]
    }

# ==================== TEAM ENDPOINTS ====================
@app.get("/teams")
def get_teams():
    """Get all teams"""
    teams = list(TEAMS_2025.keys())
    return {
        "teams": teams,
        "count": len(teams),
        "season": 2025
    }

@app.get("/team/{team_name}")
def get_team_info(team_name: str):
    """Get information about a specific team"""
    team_norm = normalize_team_name(team_name)
    short_name = get_team_short_name(team_norm)
    
    if short_name in TEAMS_2025:
        return TEAMS_2025[short_name]
    
    return {"error": f"Team '{team_name}' not found"}

# ==================== VENUE ENDPOINTS ====================
@app.get("/venues")
def get_venues():
    """Get all IPL 2025 venues"""
    return {
        "venues": VENUES_2025,
        "count": len(VENUES_2025),
        "season": 2025
    }

# ==================== PREDICTION ENDPOINTS ====================
@app.post("/predict/match")
def predict_match_endpoint(request: PredictionRequest, db = Depends(get_db)):
    """Predict match winner with detailed analysis"""
    try:
        # Make prediction (works for both authenticated and demo users)
        prediction = predict_match(
            request.team1,
            request.team2,
            request.venue,
            request.weather,
            request.runsTeam1,
            request.runsTeam2,
            request.wicketsTeam1,
            request.wicketsTeam2
        )
        
        # If username provided, deduct tokens from database
        username = request.username
        if username:
            user = get_user_by_username(db, username)
            if not user:
                # User doesn't exist yet - allow prediction but don't charge
                prediction['note'] = "Demo prediction (user account not found)"
                return prediction
            
            if user.tokens < 10:
                return {"ok": False, "error": "insufficient tokens"}
            
            # Deduct tokens
            deduct_tokens(db, username, 10)
            prediction['charged_user'] = username
            prediction['tokens_remaining'] = user.tokens - 10
        else:
            # No username - demo mode
            prediction['note'] = "Demo prediction (not charged)"
        
        return prediction
    except Exception as e:
        print(f"Prediction error: {e}")
        return {"error": str(e)}

@app.post("/predict/wickets")
def predict_wickets_endpoint(request: WicketPredictionRequest):
    """Predict wickets and match statistics"""
    try:
        prediction = predict_wickets(
            request.team1,
            request.team2,
            request.overs,
            request.wicketsTeam1,
            request.wicketsTeam2
        )
        return prediction
    except Exception as e:
        return {"error": str(e)}
@app.post("/upload/scorecard")
async def upload_scorecard(file: UploadFile = File(...)):
    os.makedirs(os.path.join(STORAGE_DIR, "uploads"), exist_ok=True)
    save_path = os.path.join(STORAGE_DIR, "uploads", file.filename)
    contents = await file.read()
    with open(save_path, "wb") as fh:
        fh.write(contents)
    try:
        df = pd.read_csv(save_path)
        # simple analysis: top scorer and top wicket taker from CSV columns 'batsman','runs','bowler','wickets' if present
        top_bats = df.groupby('batsman')['runs'].sum().sort_values(ascending=False).head(3).to_dict() if 'batsman' in df.columns and 'runs' in df.columns else {}
        top_bowl = df.groupby('bowler')['wickets'].sum().sort_values(ascending=False).head(3).to_dict() if 'bowler' in df.columns and 'wickets' in df.columns else {}
        return {"ok": True, "path": save_path, "top_batsmen": top_bats, "top_bowlers": top_bowl}
    except Exception as e:
        return {"ok": False, "error": str(e)}
@app.get("/predict")
def predict_get(
    team1: str,
    team2: str,
    team1_score: int,
    team2_score: int,
    overs: int,
    venue: str = "Neutral",
    weather: str = "Sunny"
):
    """Quick prediction endpoint (GET)"""
    try:
        prediction = predict_match(
            team1,
            team2,
            venue,
            weather,
            team1_score,
            team2_score,
            3,
            3
        )
        return prediction
    except Exception as e:
        return {"error": str(e)}

# ==================== PLAYER ENDPOINTS ====================
@app.get("/players")
def get_players(team: str = Query(None)):
    """Get players data"""
    try:
        players_path = os.path.join(os.path.dirname(__file__), "data", "players1.csv")
        
        if not os.path.exists(players_path):
            return {
                "message": "Players data not available yet",
                "teams": list(TEAMS_2025.keys())
            }
        
        df = pd.read_csv(players_path)
        df = df.replace({np.nan: None})
        
        # Add team information to each player
        df['Team'] = df['Player_Name'].apply(lambda x: PLAYER_TO_TEAM.get(x))
        
        if team:
            df = df[df["Team"] == team.upper()]
        
        players = df.to_dict(orient="records")
        return {
            "players": players,
            "count": len(players)
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/pvp/players")
# ...existing code...
def pvp_players():
    """Return unique player lists (batsmen and bowlers) from the ball-by-ball dataset."""
    # Prefer ball-by-ball dataset when available; otherwise build a catalog from aggregated CSVs
    try:
        df = pvp_utils.load_ball_data()
        # find columns
        batsman_col = None
        bowler_col = None
        for c in df.columns:
            lc = c.lower()
            if lc == 'batsman' and batsman_col is None:
                batsman_col = c
            if lc == 'bowler' and bowler_col is None:
                bowler_col = c

        if batsman_col is None or bowler_col is None:
            batsman_col = pvp_utils.safe_get_column(df, ['batsman','batsman_name'])
            bowler_col = pvp_utils.safe_get_column(df, ['bowler','bowler_name'])

        if batsman_col is None or bowler_col is None:
            raise HTTPException(status_code=500, detail='Could not identify batsman/bowler columns in ball-by-ball dataset')

        batsmen = sorted(df[batsman_col].dropna().astype(str).str.strip().unique().tolist())
        bowlers = sorted(df[bowler_col].dropna().astype(str).str.strip().unique().tolist())

        return {"batsmen": batsmen, "bowlers": bowlers, "counts": {"batsmen": len(batsmen), "bowlers": len(bowlers)}}
    except FileNotFoundError:
        # build catalog from aggregated CSVs
        try:
            catalog = pvp_utils.build_player_catalog()
            batsmen = []
            bowlers = []
            for name, ent in catalog.items():
                role = (ent.get('role') or '').lower()
                if 'all-rounder' in role or 'allrounder' in role or 'batsman' in role or 'wicketkeeper' in role:
                    batsmen.append(name)
                if 'all-rounder' in role or 'allrounder' in role or 'bowler' in role:
                    bowlers.append(name)

            # Also augment lists using players1.csv bowling info if available
            players_path = os.path.join(os.path.dirname(__file__), "data", "players1.csv")
            if os.path.exists(players_path):
                import pandas as _pd
                try:
                    pdf = _pd.read_csv(players_path)
                    for _, row in pdf.iterrows():
                        name = str(row.get('Player_Name') or '').strip()
                        if not name:
                            continue
                        bowling_skill = str(row.get('Bowling_Skill') or '').strip()
                        has_bowled = bool(bowling_skill and bowling_skill.upper() != 'NULL')
                        if has_bowled:
                            bowlers.append(name)
                        else:
                            batsmen.append(name)
                except Exception:
                    pass

            batsmen = sorted(list(set(batsmen)))
            bowlers = sorted(list(set(bowlers)))
            return {"batsmen": batsmen, "bowlers": bowlers, "counts": {"batsmen": len(batsmen), "bowlers": len(bowlers)}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/pvp/search")
def pvp_search(q: str = Query(None), limit: int = 50, role: str = Query(None)):
    """Async-search-friendly endpoint returning player profiles (name, role, has_batted, has_bowled).

    Optional `role` filter: 'batsman' or 'bowler' to return only matching players.
    """
    try:
        results = pvp_utils.search_players(query=q, limit=limit)
        # apply role filter if requested
        if role:
            r = role.strip().lower()
            if r == 'batsman':
                results = [x for x in results if x.get('has_batted')]
            elif r == 'bowler':
                results = [x for x in results if x.get('has_bowled')]
        return {"ok": True, "results": results, "count": len(results)}
    except FileNotFoundError:
        # Ball-by-ball not available — fallback to players1.csv if present so frontend still has selectable names
        players_path = os.path.join(os.path.dirname(__file__), "data", "players1.csv")
        if not os.path.exists(players_path):
            raise HTTPException(status_code=404, detail="Ball-by-ball dataset not found and players1.csv missing")
        try:
            pdf = pd.read_csv(players_path)
            ql = (q or '').strip().lower()
            out = []
            for _, row in pdf.iterrows():
                name = str(row.get('Player_Name') or '').strip()
                if not name:
                    continue
                if ql and ql not in name.lower():
                    continue
                bowling_skill = str(row.get('Bowling_Skill') or '').strip()
                has_bowled = bool(bowling_skill and bowling_skill.upper() != 'NULL')
                role = 'Bowler' if has_bowled else 'Batsman'
                item = {"name": name, "role": role, "has_batted": True, "has_bowled": has_bowled}
                # apply role filter if requested
                if role:
                    rr = role.strip().lower()
                    if rr == 'batsman' and not item['has_batted']:
                        continue
                    if rr == 'bowler' and not item['has_bowled']:
                        continue
                out.append(item)
                if len(out) >= limit:
                    break
            return {"ok": True, "results": out, "count": len(out)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pvp/player")
def pvp_player(name: str = Query(...)):
    """Return enriched player profile built from aggregated datasets if available."""
    try:
        profile = pvp_utils.get_player_profile(name)
        return {"ok": True, "profile": profile}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pvp")
def pvp_endpoint(batsman: str = Query(...), bowler: str = Query(...)):
    """Compute PVP stats for a batsman vs bowler using aggregated datasets."""
    try:
        # Try aggregated CSV-based comparison first (most reliable without ball-by-ball)
        try:
            res = pvp_utils.compute_pvp_from_aggregates(batsman, bowler)
            return {"ok": True, "data": res}
        except Exception as agg_err:
            # Fallback to ball-by-ball compute_pvp if aggregates fail
            try:
                res = pvp_utils.compute_pvp(batsman, bowler)
                return {"ok": True, "data": res}
            except Exception as ball_err:
                raise ValueError(f"Aggregates failed: {str(agg_err)}; Ball-by-ball failed: {str(ball_err)}")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MATCH ENDPOINTS ====================
@app.get("/matches")
def get_matches():
    """Get match history"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), "data", "matches.csv")
        
        if not os.path.exists(data_path):
            return {
                "message": "Match data not available",
                "teams": list(TEAMS_2025.keys())
            }
        
        df = pd.read_csv(data_path)
        df = df.astype(str).replace("nan", "")
        
        return {
            "matches": df.to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}

# ==================== HEALTH CHECK ====================
@app.get("/health")
def health_check():
    """Check API health status"""
    return {
        "status": "API is running",
        "version": "2.0",
        "season": 2025,
        "teams": len(TEAMS_2025),
        "venues": len(VENUES_2025)
    }

# ==================== STATISTICS ENDPOINTS ====================
@app.get("/stats/teams")
def get_teams_stats():
    """Get teams statistics"""
    stats = []
    for team_code, team_info in TEAMS_2025.items():
        stats.append({
            "name": team_code,
            "fullName": team_info["fullName"],
            "captain": team_info["captain"],
            "titles": team_info["titles"],
            "topScorer": team_info["topScorer"],
            "topBowler": team_info["topBowler"]
        })
    return {"teams_stats": stats, "count": len(stats)}

@app.get("/stats/compare")
def compare_teams(team1: str, team2: str):
    """Compare two teams"""
    team1_norm = normalize_team_name(team1)
    team2_norm = normalize_team_name(team2)
    
    short1 = get_team_short_name(team1_norm)
    short2 = get_team_short_name(team2_norm)
    
    if short1 not in TEAMS_2025 or short2 not in TEAMS_2025:
        return {"error": "One or both teams not found"}
    
    return {
        "team1": TEAMS_2025[short1],
        "team2": TEAMS_2025[short2],
        "comparison": {
            "titles": TEAMS_2025[short1]["titles"] - TEAMS_2025[short2]["titles"],
            "message": f"{short1} has {abs(TEAMS_2025[short1]['titles'] - TEAMS_2025[short2]['titles'])} more titles" if TEAMS_2025[short1]["titles"] != TEAMS_2025[short2]["titles"] else "Teams have equal titles"
        }
    }

# ==================== SIMPLE JSON STORAGE FOR USERS & PREDICTIONS ====================
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(STORAGE_DIR, "users.json")
PREDICTIONS_FILE = os.path.join(STORAGE_DIR, "predictions.json")
REFERRALS_FILE = os.path.join(STORAGE_DIR, "referrals.json")
os.makedirs(STORAGE_DIR, exist_ok=True)
for f in (USERS_FILE, PREDICTIONS_FILE):
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as fh:
            json.dump([], fh)
for f in (REFERRALS_FILE,):
    if not os.path.exists(f):
        with open(f, "w", encoding="utf-8") as fh:
            json.dump([], fh)

def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except:
            return []

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)

def _hash_password(password: str, salt: Optional[str] = None):
    if salt is None:
        salt = uuid.uuid4().hex
    h = hashlib.sha256((salt + (password or '')).encode('utf-8')).hexdigest()
    return salt, h


def _safe_user_for_client(user: dict):
    u = dict(user)
    u.pop('password_hash', None)
    u.pop('salt', None)
    return u


def _generate_referral_code(existing_codes: set):
    # short unique code
    for _ in range(10):
        code = uuid.uuid4().hex[:8].upper()
        if code not in existing_codes:
            return code
    # fallback
    return uuid.uuid4().hex[:8].upper()


@app.post("/users/register")
def register_user(data: dict, db = Depends(get_db)):
    """Register a new user using unified database"""
    
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    display_name = data.get("display_name", username)
    
    if not username:
        return {"ok": False, "error": "username is required"}
    if not password:
        return {"ok": False, "error": "password is required"}
    
    try:
        user = create_user(
            db,
            username=username,
            display_name=display_name,
            password=password,
            email=f"{username}@cricket.local"
        )
        
        return {
            "ok": True,
            "user": user.to_dict(),
            "token": str(uuid.uuid4())
        }
    except ValueError as e:
        if "already exists" in str(e):
            return {"ok": False, "error": "username exists"}
        else:
            return {"ok": False, "error": str(e)}
    except Exception as e:
        print(f"Registration error: {e}")
        return {"ok": False, "error": "Registration failed"}


@app.post("/users/login")
def login_user(data: dict, db = Depends(get_db)):
    """Authenticate a user using unified database"""
    
    username_or_email = data.get("username", "").strip() or data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    if not username_or_email or not password:
        return {"ok": False, "error": "username and password are required"}

    try:
        # Authenticate user
        user = authenticate_user(db, username_or_email, password)
        
        if user:
            return {
                "ok": True,
                "user": user.to_dict(),
                "token": str(uuid.uuid4())
            }
        else:
            return {"ok": False, "error": "Invalid username or password"}
            
    except Exception as e:
        print(f"Login error: {e}")
        return {"ok": False, "error": "Login failed"}

@app.post("/fantasy/recommend")
def fantasy_recommend(budget: int = 100):
    players_path = os.path.join(os.path.dirname(__file__), "data", "players1.csv")
    if not os.path.exists(players_path):
        return {"ok": False, "error": "players data not found"}
    df = pd.read_csv(players_path)
    # heuristic: prefer highest 'Runs' or 'Avg' column if present
    score_col = None
    for col in ['Runs','runs','AVG','avg','Score']:
        if col in df.columns:
            score_col = col; break
    if score_col:
        df = df.sort_values(by=score_col, ascending=False)
    df = df.head(20)
    # pick 11
    pick = df.head(11).to_dict(orient='records')
    return {"ok": True, "picks": pick}
# ...existing code...
@app.get("/users/{username}")
def get_user(username: str):
    users = read_json(USERS_FILE)
    u = next((x for x in users if x["username"] == username), None)
    if not u:
        return {"ok": False, "error": "user not found"}
    safe = dict(u)
    safe.pop('password_hash', None)
    safe.pop('salt', None)
    return {"ok": True, "user": safe}


@app.get("/users/{username}/referral")
def get_referral(username: str, base_url: str = Query(None)):
    """Return user's referral code and a shareable link.

    Optional `base_url` query param can override the frontend signup base.
    """
    users = read_json(USERS_FILE)
    u = next((x for x in users if x["username"] == username), None)
    if not u:
        return {"ok": False, "error": "user not found"}
    code = u.get('referral_code')
    if not code:
        return {"ok": False, "error": "no referral code found"}
    frontend = base_url or os.environ.get('FRONTEND_URL') or 'http://127.0.0.1:3000'
    link = f"{frontend.rstrip('/')}?ref={code}"
    return {"ok": True, "referral_code": code, "referral_link": link}
# ...existing code...
@app.get("/provenance/h2h")
def provenance_h2h(team1: str, team2: str):
    path = os.path.join(os.path.dirname(__file__), "data", "headtohead.csv")
    if not os.path.exists(path):
        return {"ok": False, "error": "headtohead.csv not found"}
    df = pd.read_csv(path, dtype=str)
    filt = df[(df['team1'].str.upper()==team1.upper()) & (df['team2'].str.upper()==team2.upper()) | (df['team1'].str.upper()==team2.upper()) & (df['team2'].str.upper()==team1.upper())]
    return {"ok": True, "matches": filt.to_dict(orient='records')}
# ...existing code...

@app.post("/users/{username}/predictions")
def save_prediction(username: str, payload: dict):
    users = read_json(USERS_FILE)
    if not any(u["username"] == username for u in users):
        return {"ok": False, "error": "user not found"}
    # deduct tokens for prediction (10 tokens)
    users = read_json(USERS_FILE)
    usr = next((u for u in users if u.get('username') == username), None)
    if not usr:
        return {"ok": False, "error": "user not found"}
    if int(usr.get('tokens', 0)) < 10:
        return {"ok": False, "error": "insufficient tokens"}
    usr['tokens'] = int(usr.get('tokens', 0)) - 10
    write_json(USERS_FILE, users)

    preds = read_json(PREDICTIONS_FILE)
    entry = {
        "id": str(uuid.uuid4()),
        "user": username,
        "timestamp": datetime.utcnow().isoformat(),
        "input": payload.get("input"),
        "result": payload.get("result"),
        "note": payload.get("note")
    }
    preds.append(entry)
    write_json(PREDICTIONS_FILE, preds)
    return {"ok": True, "prediction": entry}

@app.get("/users/{username}/predictions")
def get_user_predictions(username: str):
    preds = read_json(PREDICTIONS_FILE)
    user_preds = [p for p in preds if p["user"] == username]
    return {"ok": True, "predictions": user_preds}

@app.get("/leaderboard")
def leaderboard(top: int = 20):
    preds = read_json(PREDICTIONS_FILE)
    counts = {}
    for p in preds:
        counts[p["user"]] = counts.get(p["user"], 0) + 1
    arr = sorted([{"user": k, "predictions": v} for k, v in counts.items()], key=lambda x: -x["predictions"])
    return {"top": arr[:top]}

@app.get("/reports/predictions.csv")
def export_predictions_csv():
    preds = read_json(PREDICTIONS_FILE)
    csv_path = os.path.join(STORAGE_DIR, "predictions_export.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id","user","timestamp","team1","team2","result","note"])
        for p in preds:
            inp = p.get("input") or {}
            res = p.get("result") or {}
            writer.writerow([p["id"], p["user"], p["timestamp"], inp.get("team1"), inp.get("team2"), res.get("predicted_winner"), p.get("note")])
    return {"ok": True, "path": csv_path}

# ==================== ADMIN (DEV) ENDPOINTS ====================
@app.get("/_admin/list_users")
def admin_list_users():
    users = read_json(USERS_FILE)
    out = []
    for u in users:
        uu = dict(u)
        uu.pop('password_hash', None)
        uu.pop('salt', None)
        out.append(uu)
    return out

@app.get("/_admin/list_predictions")
def admin_list_predictions():
    return read_json(PREDICTIONS_FILE)


@app.get("/_admin/list_referrals")
def admin_list_referrals():
    return read_json(REFERRALS_FILE)


# ================ BALANCE / TOKEN ENDPOINTS ================
@app.get("/users/{username}/balance")
def user_balance(username: str):
    """Return authoritative token balance for a user. If tokens are missing, default to 100 (non-destructive).

    Response: { ok: True, username, tokens, default_applied: bool }
    """
    users = read_json(USERS_FILE)
    u = next((x for x in users if x.get("username") == username), None)
    if not u:
        return {"ok": False, "error": "user not found"}
    tokens = u.get('tokens')
    default_applied = False
    if tokens is None:
        tokens = 100
        default_applied = True
    return {"ok": True, "username": username, "tokens": int(tokens), "default_applied": default_applied}


@app.post("/_admin/ensure_default_tokens")
def admin_ensure_default_tokens():
    """Admin-only (dev) endpoint: set tokens=100 for users missing a tokens field.

    This endpoint is safe to run multiple times; it will not overwrite existing token balances.
    Returns a summary of how many users were updated and a sample of updated usernames.
    """
    users = read_json(USERS_FILE)
    updated = []
    for u in users:
        if 'tokens' not in u or u.get('tokens') is None:
            u['tokens'] = 100
            updated.append(u.get('username'))
    if updated:
        write_json(USERS_FILE, users)
    return {"ok": True, "updated_count": len(updated), "updated_users": updated}

# ==================== SPIN WHEEL ENDPOINTS ====================
@app.post("/users/{username}/spin")
def spin_wheel(username: str):
    """Spin the wheel and get a random reward. Max 2 spins per day."""
    users = read_json(USERS_FILE)
    user = next((u for u in users if u.get('username') == username), None)
    if not user:
        return {"ok": False, "error": "user not found"}
    
    # Check and track daily spins
    today = datetime.utcnow().date().isoformat()
    spin_data = user.get('spin_data', {})
    
    last_spin_date = spin_data.get('date')
    if last_spin_date != today:
        # Reset spins for new day
        spin_data = {'date': today, 'count': 0}
    
    spins_left = 2 - spin_data.get('count', 0)
    if spins_left <= 0:
        return {"ok": False, "error": "no spins left today", "spins_left": 0}
    
    # Random reward: 5, 15, 50, or 100 tokens
    rewards = [5, 15, 50, 100]
    reward = random.choice(rewards)
    
    # Update user tokens and spins
    user['tokens'] = int(user.get('tokens', 0)) + reward
    spin_data['count'] = spin_data.get('count', 0) + 1
    spin_data['last_reward'] = reward
    spin_data['last_spin'] = datetime.utcnow().isoformat()
    user['spin_data'] = spin_data
    
    write_json(USERS_FILE, users)
    
    return {
        "ok": True,
        "reward": reward,
        "tokens_remaining": user['tokens'],
        "spins_left": 2 - spin_data['count']
    }

@app.get("/users/{username}/spin_status")
def get_spin_status(username: str):
    """Get user's spin status (spins left today, last reward)."""
    users = read_json(USERS_FILE)
    user = next((u for u in users if u.get('username') == username), None)
    if not user:
        return {"ok": False, "error": "user not found"}
    
    today = datetime.utcnow().date().isoformat()
    spin_data = user.get('spin_data', {})
    
    last_spin_date = spin_data.get('date')
    if last_spin_date != today:
        # Reset spins for new day
        spin_data = {'date': today, 'count': 0}
    
    spins_left = 2 - spin_data.get('count', 0)
    last_reward = spin_data.get('last_reward')
    
    return {
        "ok": True,
        "spins_left": spins_left,
        "last_reward": last_reward,
        "date": today
    }

# ...existing code...