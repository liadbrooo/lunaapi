from redbot.core import commands
from redbot.core.bot import Red
from redbot.core import checks
from redbot.core.utils.chat_formatting import box, pagify
import discord
from discord.ext import commands as dcommands
import aiohttp
import asyncio

class LunaDoc(commands.Cog):
    """Ein Cog zur Interaktion mit der Luna API."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.base_url = "https://api.lunadoc.net/api/public/v1"  # Standard URL, kann konfiguriert werden
        self.token = None  # Token kann konfiguriert werden

    async def api_request(self, endpoint: str, params: dict = None):
        """Führt eine API-Anfrage durch."""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    return {"error": "Ungültiger oder fehlender API-Token."}
                elif response.status == 404:
                    return {"error": "Ressource nicht gefunden."}
                else:
                    return {"error": f"API-Fehler: Status {response.status}"}

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.guild_only()
    async def luna_group(self, ctx):
        """Befehlsgruppe für Luna-API-Abfragen."""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Zeigt den Serverstatus der Luna API an."""
        data = await self.api_request("server/status")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        embed = discord.Embed(title="Luna Server Status", color=discord.Color.green())
        for key, value in data.items():
            embed.add_field(name=key, value=str(value), inline=True)
        await ctx.send(embed=embed)

    @luna_group.command(name="players")
    async def luna_players(self, ctx, online: bool = False, search: str = None, limit: int = 50):
        """Zeigt eine Liste der Spieler an."""
        params = {}
        if online:
            params["online"] = "true"
        if search:
            params["search"] = search
        params["limit"] = str(limit)
        
        data = await self.api_request("players", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Spieler gefunden.")
            return

        embed = discord.Embed(title="Spielerliste", color=discord.Color.blue())
        for player in data[:10]:  # Zeige max. 10 Spieler im Embed
            name = player.get("name", "Unbekannt")
            uuid = player.get("id", "N/A")
            embed.add_field(name=name, value=f"ID: `{uuid}`", inline=False)
        
        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Spieler.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="player")
    async def luna_player(self, ctx, player_id: str):
        """Zeigt Details zu einem spezifischen Spieler an."""
        data = await self.api_request(f"players/{player_id}")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        embed = discord.Embed(title=f"Spieler: {data.get('name', 'Unbekannt')}", color=discord.Color.blue())
        embed.add_field(name="ID", value=data.get("id", "N/A"), inline=True)
        embed.add_field(name="Name", value=data.get("name", "N/A"), inline=True)
        
        # Weitere Felder je nach API-Antwort hinzufügen
        for key, value in data.items():
            if key not in ["id", "name"]:
                embed.add_field(name=key, value=str(value), inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, active: bool = True):
        """Zeigt die Bans an."""
        params = {"active": "true" if active else "false"}
        data = await self.api_request("bans", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Bans gefunden.")
            return

        embed = discord.Embed(title="Bans", color=discord.Color.red())
        for ban in data[:10]:  # Zeige max. 10 Bans
            player = ban.get("player", {}).get("name", "Unbekannt")
            reason = ban.get("reason", "Kein Grund angegeben")
            embed.add_field(name=player, value=f"Grund: {reason}", inline=False)
        
        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Bans.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="cases")
    async def luna_cases(self, ctx, case_type: str = None):
        """Zeigt die Fälle an."""
        params = {}
        if case_type:
            params["type"] = case_type
        
        data = await self.api_request("cases", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Fälle gefunden.")
            return

        embed = discord.Embed(title="Fälle", color=discord.Color.orange())
        for case in data[:10]:  # Zeige max. 10 Fälle
            case_id = case.get("id", "N/A")
            case_type = case.get("type", "Unbekannt")
            embed.add_field(name=f"Fall #{case_id}", value=f"Typ: {case_type}", inline=False)
        
        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Fälle.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """Zeigt die Mitarbeiterliste an."""
        data = await self.api_request("staff")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Mitarbeiter gefunden.")
            return

        embed = discord.Embed(title="Mitarbeiter", color=discord.Color.gold())
        for member in data:
            name = member.get("name", "Unbekannt")
            role = member.get("role", "N/A")
            embed.add_field(name=name, value=f"Rolle: {role}", inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata")
    async def luna_gamedata(self, ctx, category: str, search: str = None, limit: int = 50):
        """Zeigt Spieldaten für eine Kategorie an."""
        params = {"limit": str(limit)}
        if search:
            params["search"] = search
        
        data = await self.api_request(f"gamedata/{category}", params)
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send(f"Keine Spieldaten für Kategorie '{category}' gefunden.")
            return

        embed = discord.Embed(title=f"Spieldaten: {category}", color=discord.Color.purple())
        for entry in data[:10]:  # Zeige max. 10 Einträge
            entry_id = entry.get("id", "N/A")
            name = entry.get("name", "Unbekannt")
            embed.add_field(name=name, value=f"ID: `{entry_id}`", inline=False)
        
        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Einträge.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """Zeigt die neuesten Absturzberichte an."""
        data = await self.api_request("crashes")
        if "error" in data:
            await ctx.send(f"Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Absturzberichte gefunden.")
            return

        embed = discord.Embed(title="Absturzberichte", color=discord.Color.dark_grey())
        for crash in data[:10]:  # Zeige max. 10 Berichte
            crash_id = crash.get("id", "N/A")
            timestamp = crash.get("timestamp", "N/A")
            embed.add_field(name=f"Crash #{crash_id}", value=f"Zeit: {timestamp}", inline=False)
        
        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Berichte.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="set")
    @checks.is_owner()
    async def luna_set(self, ctx, setting: str, *, value: str):
        """Setzt Konfigurationseinstellungen (nur Bot-Besitzer)."""
        if setting.lower() == "token":
            self.token = value
            await ctx.send("API-Token wurde gesetzt.")
        elif setting.lower() == "url":
            self.base_url = value
            await ctx.send("API-Basis-URL wurde gesetzt.")
        else:
            await ctx.send("Ungültige Einstellung. Verfügbare Einstellungen: `token`, `url`.")

def setup(bot: Red):
    bot.add_cog(LunaDoc(bot))
