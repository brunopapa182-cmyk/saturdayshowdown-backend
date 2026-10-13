import requests

# NHL API endpoint for full season schedule
NHL_SCHEDULE_URL = "https://statsapi.web.nhl.com/api/v1/schedule?season=20242025"


def fetch_full_season_schedule():
    """
    Fetches the full NHL season schedule from the official NHL Stats API.
    Returns a list of games.
    """

    response = requests.get(NHL_SCHEDULE_URL)

    if response.status_code != 200:
        raise Exception("Failed to fetch NHL schedule")

    data = response.json()

    games = []

    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            games.append(game)

    return games
