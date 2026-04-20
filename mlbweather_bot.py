import discord
from discord import app_commands
import requests
import os

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

STADIUMS = {
    "los angeles angels": {"team": "Los Angeles Angels", "stadium": "Angel Stadium", "lat": 33.799572, "lon": -117.889031},
    "arizona diamondbacks": {"team": "Arizona Diamondbacks", "stadium": "Chase Field", "lat": 33.452922, "lon": -112.038669},
    "atlanta braves": {"team": "Atlanta Braves", "stadium": "Truist Park", "lat": 33.8908, "lon": -84.4678},
    "baltimore orioles": {"team": "Baltimore Orioles", "stadium": "Oriole Park at Camden Yards", "lat": 39.285243, "lon": -76.620103},
    "boston red sox": {"team": "Boston Red Sox", "stadium": "Fenway Park", "lat": 42.346613, "lon": -71.098817},
    "chicago cubs": {"team": "Chicago Cubs", "stadium": "Wrigley Field", "lat": 41.947201, "lon": -87.656413},
    "chicago white sox": {"team": "Chicago White Sox", "stadium": "Guaranteed Rate Field", "lat": 41.830883, "lon": -87.635083},
    "cincinnati reds": {"team": "Cincinnati Reds", "stadium": "Great American Ball Park", "lat": 39.107183, "lon": -84.507713},
    "cleveland guardians": {"team": "Cleveland Guardians", "stadium": "Progressive Field", "lat": 41.495149, "lon": -81.68709},
    "colorado rockies": {"team": "Colorado Rockies", "stadium": "Coors Field", "lat": 39.75698, "lon": -104.965329},
    "detroit tigers": {"team": "Detroit Tigers", "stadium": "Comerica Park", "lat": 42.346354, "lon": -83.059619},
    "miami marlins": {"team": "Miami Marlins", "stadium": "loanDepot park", "lat": 25.7783, "lon": -80.2196},
    "houston astros": {"team": "Houston Astros", "stadium": "Minute Maid Park", "lat": 29.76045, "lon": -95.369784},
    "kansas city royals": {"team": "Kansas City Royals", "stadium": "Kauffman Stadium", "lat": 39.10222, "lon": -94.583559},
    "los angeles dodgers": {"team": "Los Angeles Dodgers", "stadium": "Dodger Stadium", "lat": 34.072437, "lon": -118.246879},
    "milwaukee brewers": {"team": "Milwaukee Brewers", "stadium": "American Family Field", "lat": 43.04205, "lon": -87.905599},
    "minnesota twins": {"team": "Minnesota Twins", "stadium": "Target Field", "lat": 44.974346, "lon": -93.259616},
    "washington nationals": {"team": "Washington Nationals", "stadium": "Nationals Park", "lat": 38.8728, "lon": -77.0075},
    "new york mets": {"team": "New York Mets", "stadium": "Citi Field", "lat": 40.75535, "lon": -73.843219},
    "new york yankees": {"team": "New York Yankees", "stadium": "Yankee Stadium", "lat": 40.819782, "lon": -73.929939},
    "oakland athletics": {"team": "Oakland Athletics", "stadium": "Sutter Health Park", "lat": 38.5686, "lon": -121.4934},
    "philadelphia phillies": {"team": "Philadelphia Phillies", "stadium": "Citizens Bank Park", "lat": 39.952313, "lon": -75.162392},
    "pittsburgh pirates": {"team": "Pittsburgh Pirates", "stadium": "PNC Park", "lat": 40.461503, "lon": -80.008924},
    "st. louis cardinals": {"team": "St. Louis Cardinals", "stadium": "Busch Stadium", "lat": 38.629683, "lon": -90.188247},
    "san diego padres": {"team": "San Diego Padres", "stadium": "Petco Park", "lat": 32.752148, "lon": -117.143635},
    "san francisco giants": {"team": "San Francisco Giants", "stadium": "Oracle Park", "lat": 37.77987, "lon": -122.389754},
    "seattle mariners": {"team": "Seattle Mariners", "stadium": "T-Mobile Park", "lat": 47.60174, "lon": -122.330829},
    "tampa bay rays": {"team": "Tampa Bay Rays", "stadium": "Tropicana Field", "lat": 27.768487, "lon": -82.648191},
    "texas rangers": {"team": "Texas Rangers", "stadium": "Globe Life Field", "lat": 32.750156, "lon": -97.081117},
    "toronto blue jays": {"team": "Toronto Blue Jays", "stadium": "Rogers Centre", "lat": 43.641653, "lon": -79.3917},
}

def get_cardinal(degrees):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(degrees / 22.5) % 16]

def get_weather(team_input):
    key = team_input.lower().strip()
    if key not in STADIUMS:
        for k in STADIUMS:
            if key in k or STADIUMS[k]["team"].lower() in key:
                key = k
                break
        else:
            return None
    data = STADIUMS[key]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={data['lat']}&longitude={data['lon']}&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=auto&temperature_unit=fahrenheit&wind_speed_unit=mph"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    current = resp.json()["current"]
    codes = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle", 61: "Light rain", 63: "Moderate rain", 65: "Heavy rain", 71: "Light snow", 73: "Moderate snow", 75: "Heavy snow", 95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"}
    condition = codes.get(current["weather_code"], f"Code {current['weather_code']}")
    wind_dir = get_cardinal(current["wind_direction_10m"])
    return {
        "team": data["team"], "stadium": data["stadium"],
        "temp": round(current["temperature_2m"]), "feels_like": round(current["apparent_temperature"]),
        "humidity": current["relative_humidity_2m"], "precip": current["precipitation"],
        "condition": condition, "wind_speed": round(current["wind_speed_10m"]),
        "wind_dir": wind_dir, "wind_gusts": round(current["wind_gusts_10m"]), "cloud": current["cloud_cover"]
    }

@tree.command(name="mlbweather", description="Get current weather + wind at any MLB stadium")
@app_commands.describe(team="Team name (e.g. Phillies, Yankees, Braves)")
async def mlbweather(interaction: discord.Interaction, team: str):
    await interaction.response.defer()
    weather = get_weather(team)
    if not weather:
        await interaction.followup.send(f"❌ Couldn't find stadium for **{team}**. Try `/listteams`!")
        return
    embed = discord.Embed(title=f"🌤️ {weather['team']} @ {weather['stadium']}", description=f"**{weather['condition']}**", color=0x00ff00)
    embed.add_field(name="Temperature", value=f"{weather['temp']}°F (feels like {weather['feels_like']}°F)", inline=True)
    embed.add_field(name="Humidity", value=f"{weather['humidity']}%", inline=True)
    embed.add_field(name="Precipitation", value=f"{weather['precip']} mm", inline=True)
    embed.add_field(name="Wind", value=f"**{weather['wind_speed']} mph {weather['wind_dir']}** (gusts to {weather['wind_gusts']} mph)", inline=False)
    embed.add_field(name="Cloud Cover", value=f"{weather['cloud']}%", inline=True)
    embed.set_footer(text="Data from Open-Meteo • Real-time • Perfect for game-day")
    await interaction.followup.send(embed=embed)

@tree.command(name="listteams", description="List all supported MLB teams")
async def listteams(interaction: discord.Interaction):
    teams = "\n".join([f"• {info['team']}" for info in STADIUMS.values()])
    await interaction.response.send_message(f"**Supported MLB Teams:**\n{teams}", ephemeral=True)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ MLB Weather Bot is online as {client.user}")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        token = "YOUR_BOT_TOKEN_HERE"
    client.run(token)
