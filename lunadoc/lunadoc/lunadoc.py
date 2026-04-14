import aiohttp
import discord
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import box, pagify

class LunaDoc(commands.Cog):
    """Interaktion mit der Luna API."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        
        default_global = {
            "api_token": "",
            "base_url": "https://api.lunadoc.de/api/public/v1"  # Standard URL, anpassbar
        }
        self.config.register_global(**default_global)
        
        self.session = None

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def api_request(self, endpoint: str, params: dict = None):
        """Führt eine Anfrage an die Luna API durch."""
        base_url = await self.config.base_url()
        token = await self.config.api_token()
        url = f"{base_url}{endpoint}"
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 401:
                    return {"error": "Ungültiger oder fehlender API-Token."}
                elif resp.status == 404:
                    return {"error": "Ressource nicht gefunden."}
                else:
                    return {"error": f"Fehler {resp.status}: {resp.reason}"}
        except Exception as e:
            return {"error": f"Verbindungsfehler: {str(e)}"}

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.guild_only()
    async def luna_group(self, ctx):
        """Befehle für die Luna API Interaktion."""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Zeigt den Serverstatus der Luna API."""
        data = await self.api_request("/server/status")
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return

        embed = discord.Embed(title="🖥️ Luna Server Status", color=discord.Color.green())
        for key, value in data.items():
            embed.add_field(name=key, value=str(value), inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="spieler", aliases=["players"])
    async def luna_spieler(self, ctx, online: bool = None, suche: str = None, limit: int = 10):
        """Listet Spieler auf. Optionen: online, suche, limit."""
        params = {}
        if online is not None:
            params["online"] = str(online).lower()
        if suche:
            params["search"] = suche
        params["limit"] = limit

        data = await self.api_request("/players", params)
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return
        
        if not data:
            await ctx.send("Keine Spieler gefunden.")
            return

        embed = discord.Embed(title=f"👥 Spielerliste ({len(data)})", color=discord.Color.blue())
        
        for player in data[:10]:  # Max 10 im Embed anzeigen
            name = player.get("name", "Unbekannt")
            pid = player.get("id", "N/A")
            status = "🟢 Online" if player.get("online", False) else "🔴 Offline"
            embed.add_field(name=name, value=f"ID: `{pid}`\n{status}", inline=False)
        
        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere.")
            
        await ctx.send(embed=embed)

    @luna_group.command(name="spielerinfo", aliases=["player"])
    async def luna_spielerinfo(self, ctx, player_id: str):
        """Zeigt Details zu einem spezifischen Spieler."""
        data = await self.api_request(f"/players/{player_id}")
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return

        embed = discord.Embed(title=f"👤 Spieler: {data.get('name', 'Unbekannt')}", color=discord.Color.gold())
        embed.add_field(name="ID", value=data.get("id", "N/A"), inline=True)
        embed.add_field(name="Online", value="Ja" if data.get("online", False) else "Nein", inline=True)
        
        # Weitere Felder dynamisch hinzufügen
        for key, value in data.items():
            if key not in ["name", "id", "online"]:
                embed.add_field(name=key, value=str(value), inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, aktiv: bool = True):
        """Listet Bans auf. Standardmäßig nur aktive."""
        params = {"active": str(aktiv).lower()}
        data = await self.api_request("/bans", params)
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return
            
        if not data:
            await ctx.send("Keine Bans gefunden.")
            return

        embed = discord.Embed(title=f"🚫 {'Aktive' if aktiv else 'Alle'} Bans ({len(data)})", color=discord.Color.red())
        
        for ban in data[:5]:  # Max 5 anzeigen
            grund = ban.get("reason", "Kein Grund angegeben")
            spieler = ban.get("playerName", ban.get("playerId", "Unbekannt"))
            embed.add_field(name="Spieler", value=f"{spieler}\nGrund: {grund[:50]}...", inline=False)
            
        if len(data) > 5:
            embed.set_footer(text=f"... und {len(data) - 5} weitere.")
            
        await ctx.send(embed=embed)

    @luna_group.command(name="faelle", aliases=["cases"])
    async def luna_faelle(self, ctx, typ: str = None):
        """Listet Fälle auf. Optional nach Typ filtern."""
        params = {}
        if typ:
            params["type"] = typ
            
        data = await self.api_request("/cases", params)
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return
            
        if not data:
            await ctx.send("Keine Fälle gefunden.")
            return

        embed = discord.Embed(title=f"📁 Fälle ({len(data)})", color=discord.Color.orange())
        
        for case in data[:5]:
            titel = case.get("title", "Ohne Titel")
            case_type = case.get("type", "Unbekannt")
            embed.add_field(name=titel, value=f"Typ: {case_type}", inline=False)
            
        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """Listet das Staff-Team auf."""
        data = await self.api_request("/staff")
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return
            
        if not data:
            await ctx.send("Keine Staff-Mitglieder gefunden.")
            return

        embed = discord.Embed(title="🛡️ Luna Staff Team", color=discord.Color.purple())
        
        for member in data:
            name = member.get("name", "Unbekannt")
            role = member.get("role", "Mitglied")
            embed.add_field(name=name, value=role, inline=True)
            
        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """Listet recente Absturzberichte auf."""
        data = await self.api_request("/crashes")
        
        if "error" in data:
            await ctx.send(f"❌ Fehler: {data['error']}")
            return
            
        if not data:
            await ctx.send("Keine Absturzberichte gefunden.")
            return

        embed = discord.Embed(title=f"💥 Absturzberichte ({len(data)})", color=discord.Color.dark_grey())
        
        for crash in data[:5]:
            datum = crash.get("date", "Unbekannt")
            spieler = crash.get("player", "Unbekannt")
            embed.add_field(name="Spieler", value=f"{spieler}\nDatum: {datum}", inline=False)
            
        await ctx.send(embed=embed)

    # Konfigurationsbefehle
    @luna_group.group(name="set", aliases=["config"])
    @checks.is_owner()
    async def luna_set_group(self, ctx):
        """Konfiguration des Luna Cogs (Nur Bot-Owner)."""
        pass

    @luna_set_group.command(name="token")
    async def luna_set_token(self, ctx, token: str):
        """Setzt den API-Token für authentifizierte Anfragen."""
        await self.config.api_token.set(token)
        await ctx.send("✅ API-Token erfolgreich gespeichert.")

    @luna_set_group.command(name="url")
    async def luna_set_url(self, ctx, url: str):
        """Setzt die Basis-URL der Luna API."""
        await self.config.base_url.set(url)
        await ctx.send(f"✅ API-URL gesetzt auf: {url}")

    @luna_set_group.command(name="reset")
    async def luna_set_reset(self, ctx):
        """Setzt alle Einstellungen auf Standard zurück."""
        await self.config.api_token.set("")
        await self.config.base_url.set("https://api.lunadoc.de/api/public/v1")
        await ctx.send("✅ Einstellungen wurden zurückgesetzt.")
