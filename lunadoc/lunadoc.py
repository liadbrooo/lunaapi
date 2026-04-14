from redbot.core import commands
from redbot.core.bot import Red
from redbot.core import Config
import aiohttp
import discord
from typing import Optional

class LunaDoc(commands.Cog):
    """LunaDoc - Interaktion mit der Luna API"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {
            "api_token": None,
            "api_url": "https://api.lunadoc.net/api/public/v1"
        }
        self.config.register_global(**default_global)
        self.session = None

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def api_request(self, endpoint: str, params: dict = None):
        url = await self.config.api_url()
        token = await self.config.api_token()
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        session = await self.get_session()
        try:
            async with session.get(f"{url}{endpoint}", headers=headers, params=params) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.guild_only()
    async def luna_group(self, ctx):
        """Luna API Befehle"""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Zeigt den Serverstatus an."""
        data = await self.api_request("/server/status")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        embed = discord.Embed(title="🖥️ Server Status", color=discord.Color.green())
        for key, value in data.items():
            embed.add_field(name=key, value=str(value), inline=True)
        await ctx.send(embed=embed)

    @luna_group.command(name="players")
    async def luna_players(self, ctx, online: bool = True, limit: int = 10, search: str = None):
        """Listet Spieler auf. Optionen: online, limit, search."""
        params = {"online": str(online).lower(), "limit": limit}
        if search:
            params["search"] = search
        
        data = await self.api_request("/players", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Spieler gefunden.")
            return

        embed = discord.Embed(title="👥 Spielerliste", color=discord.Color.blue())
        for player in data[:limit]:
            name = player.get("name", "Unbekannt")
            status = "🟢 Online" if player.get("online") else "🔴 Offline"
            embed.add_field(name=name, value=status, inline=True)
        await ctx.send(embed=embed)

    @luna_group.command(name="player")
    async def luna_player(self, ctx, player_id: str):
        """Zeigt Details zu einem spezifischen Spieler."""
        data = await self.api_request(f"/players/{player_id}")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        embed = discord.Embed(title=f"👤 Spieler: {data.get('name', player_id)}", color=discord.Color.blue())
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = str(value)
            embed.add_field(name=key, value=str(value)[:1024], inline=False)
        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, active: bool = True):
        """Listet Bans auf. Option: active."""
        params = {"active": str(active).lower()}
        data = await self.api_request("/bans", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Bans gefunden.")
            return

        embed = discord.Embed(title="🚫 Bans", color=discord.Color.red())
        for ban in data[:10]:
            reason = ban.get("reason", "Kein Grund angegeben")
            player = ban.get("player", "Unbekannt")
            embed.add_field(name=player, value=reason[:1024], inline=False)
        await ctx.send(embed=embed)

    @luna_group.command(name="cases")
    async def luna_cases(self, ctx, case_type: str = None):
        """Listet Fälle auf. Option: type."""
        params = {}
        if case_type:
            params["type"] = case_type
        data = await self.api_request("/cases", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Fälle gefunden.")
            return

        embed = discord.Embed(title="📁 Fälle", color=discord.Color.orange())
        for case in data[:10]:
            title = case.get("title", "Ohne Titel")
            case_id = case.get("id", "Unbekannt")
            embed.add_field(name=f"#{case_id}: {title}", value="Details verfügbar", inline=False)
        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """Listet das Personal auf."""
        data = await self.api_request("/staff")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Mitarbeiter gefunden.")
            return

        embed = discord.Embed(title="🛡️ Personal", color=discord.Color.gold())
        for member in data:
            name = member.get("name", "Unbekannt")
            role = member.get("role", "Unbekannte Rolle")
            embed.add_field(name=name, value=role, inline=True)
        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata")
    async def luna_gamedata(self, ctx, category: str, search: str = None, limit: int = 10):
        """Listet Spieldaten einer Kategorie auf."""
        params = {"limit": limit}
        if search:
            params["search"] = search
        
        data = await self.api_request(f"/gamedata/{category}", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send(f"Keine Daten für Kategorie '{category}' gefunden.")
            return

        embed = discord.Embed(title=f"🎮 Spieldaten: {category}", color=discord.Color.purple())
        for item in data[:limit]:
            name = item.get("name", "Unbekannt")
            item_id = item.get("id", "Unbekannt")
            embed.add_field(name=name, value=f"ID: {item_id}", inline=True)
        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """Listet Absturzberichte auf."""
        data = await self.api_request("/crashes")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Absturzberichte gefunden.")
            return

        embed = discord.Embed(title="💥 Absturzberichte", color=discord.Color.dark_red())
        for crash in data[:10]:
            crash_id = crash.get("id", "Unbekannt")
            date = crash.get("date", "Unbekanntes Datum")
            embed.add_field(name=f"Crash #{crash_id}", value=date, inline=True)
        await ctx.send(embed=embed)

    @luna_group.group(name="set")
    @commands.is_owner()
    async def luna_set(self, ctx):
        """Konfiguration des Luna Cogs (Nur Owner)."""
        pass

    @luna_set.command(name="token")
    async def luna_set_token(self, ctx, token: str):
        """Setzt den API Token."""
        await self.config.api_token.set(token)
        await ctx.send("✅ API Token erfolgreich gesetzt.")

    @luna_set.command(name="url")
    async def luna_set_url(self, ctx, url: str):
        """Setzt die API Basis-URL."""
        await self.config.api_url.set(url)
        await ctx.send("✅ API URL erfolgreich gesetzt.")

async def setup(bot):
    await bot.add_cog(LunaDoc(bot))
