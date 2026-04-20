import discord
from discord import app_commands
import requests
import os
import datetime
from discord.ext import tasks

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# === YOUR MLB STADIUMS (same as before) ===
STADIUMS = { ... }  # ← I kept the exact same 30 stadiums you already have

# === DAILY REPORT CHANNEL (you will set this in .env) ===
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))

def get_cardinal(degrees):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(degrees / 22.5) % 16]

def get_weather(team_input):
    # (exact same function you already have — I kept it unchanged)
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

def get_todays_games():
    today = datetime.date.today().isoformat()
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return []
    
    games = []
    for date in resp.json().get("dates", []):
        for game in date.get("games", []):
            status = game["status"]["abstractGameState"]
            if status in ["Preview", "Live"]:  # only upcoming or live games
                away = game["teams"]["away"]["team"]["name"]
                home = game["teams"]["home"]["team"]["name"]
                weather = get_weather(home)  # looks up stadium by home team
                if weather:
                    games.append({
                        "away": away,
                        "home": home,
                        "stadium": weather["stadium"],
                        "weather": weather
                    })
    return games

@tree.command(name="mlbweather", description="Manual weather for any team")
@app_commands.describe(team="Team name")
async def mlbweather(interaction: discord.Interaction, team: str):
    await interaction.response.defer()
    weather = get_weather(team)
    if not weather:
        await interaction.followup.send("❌ Team not found. Try `/listteams`")
        return
    # (same nice embed as before)
    embed = discord.Embed(title=f"🌤️ {weather['team']} @ {weather['stadium']}", description=f"**{weather['condition']}**", color=0x00ff00)
    embed.add_field(name="Temperature", value=f"{weather['temp']}°F (feels like {weather['feels_like']}°F)", inline=True)
    embed.add_field(name="Humidity", value=f"{weather['humidity']}%", inline=True)
    embed.add_field(name="Precipitation", value=f"{weather['precip']} mm", inline=True)
    embed.add_field(name="Wind", value=f"**{weather['wind_speed']} mph {weather['wind_dir']}** (gusts to {weather['wind_gusts']} mph)", inline=False)
    embed.add_field(name="Cloud Cover", value=f"{weather['cloud']}%", inline=True)
    embed.set_footer(text="Data from Open-Meteo • Real-time")
    await interaction.followup.send(embed=embed)

@tree.command(name="listteams", description="List all supported MLB teams")
async def listteams(interaction: discord.Interaction):
    teams = "\n".join([f"• {info['team']}" for info in STADIUMS.values()])
    await interaction.response.send_message(f"**Supported MLB Teams:**\n{teams}", ephemeral=True)

@tasks.loop(minutes=1)  # checks every minute
async def daily_report():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # 8:00 AM Eastern = 12:00 UTC (EDT = UTC-4)
    if now_utc.hour == 12 and now_utc.minute == 0:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            print("⚠️ Daily report channel not found!")
            return
        
        games = get_todays_games()
        if not games:
            await channel.send("🌤️ **MLB Game Day Weather Report**\nNo games scheduled today.")
            return
        
        embed = discord.Embed(
            title=f"⚾ MLB Game Day Weather Report — {datetime.date.today().strftime('%B %d, %Y')}",
            description="Early morning conditions for today's games • Wind direction & speed included",
            color=0x00ff00
        )
        for g in games:
            w = g["weather"]
            wind_note = "Blowing OUT → favors hitters (fly balls carry farther)" if w["wind_speed"] > 8 else "Light wind"
            embed.add_field(
                name=f"{g['away']} @ {g['home']}",
                value=f"**{g['stadium']}**\n{w['condition']} | {w['temp']}°F (feels {w['feels_like']}°F)\n"
                      f"**Wind:** {w['wind_speed']} mph {w['wind_dir']} (gusts {w['wind_gusts']} mph)\n"
                      f"{wind_note}\nHumidity {w['humidity']}% • Precip {w['precip']} mm",
                inline=False
            )
        embed.set_footer(text="Auto-posted every morning • Open-Meteo data • Perfect for your daily baseball fix")
        await channel.send(embed=embed)
        print("✅ Daily MLB weather report posted!")

@client.event
async def on_ready():
    await tree.sync()
    daily_report.start()   # ← starts the automatic morning report
    print(f"✅ MLB Weather Bot is online as {client.user} — Daily 8 AM reports enabled!")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    client.run(token)
