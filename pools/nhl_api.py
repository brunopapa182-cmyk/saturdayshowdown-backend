import requests

def fetch_nhl_schedule(season: str = "20242025"):
    url = f"https://statsapi.web.nhl.com/api/v1/schedule?season={season}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
