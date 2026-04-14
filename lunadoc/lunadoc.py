import discord
from redbot.core import commands, Config
from redbot.core.utils.chat_formatting import box, pagify
import aiohttp
import asyncio

class LunaDoc(commands.Cog):
    """Interagiert mit der Luna API für Serverstatus, Spieler, Bans und mehr."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {
            "token": None,
            "base_url": "https://api.lunadoc.de/api/public/v1"  # Standard URL anpassen falls nötig
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
        """Führt einen API-Request durch."""
        base_url = await self.config.base_url()
        token = await self.config.token()
        url = f"{base_url}{endpoint}"
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        session = await self.get_session()
        
        try:
            async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                if resp.status == 401:
                    return None, "Ungültiger oder fehlender API-Token."
                elif resp.status == 404:
                    return None, "Ressource nicht gefunden."
                elif resp.status != 200:
                    return None, f"API-Fehler: {resp.status}"
                
                return await resp.json(), None
        except asyncio.TimeoutError:
            return None, "Zeitüberschreitung bei der API-Anfrage."
        except Exception as e:
            return None, f"Fehler: {str(e)}"

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.guild_only()
    async def luna_group(self, ctx):
        """Luna API Befehle."""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Zeigt den Serverstatus an."""
        data, error = await self.api_request("/server/status")
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        embed = discord.Embed(title="🖥️ Server Status", color=discord.Color.green())
        embed.add_field(name="Status", value=data.get("status", "Unbekannt"), inline=False)
        embed.add_field(name="Spieler Online", value=data.get("players_online", "N/A"), inline=True)
        embed.add_field(name="Max Spieler", value=data.get("max_players", "N/A"), inline=True)
        embed.add_field(name="Version", value=data.get("version", "N/A"), inline=True)
        embed.add_field(name="Uptime", value=data.get("uptime", "N/A"), inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="players")
    async def luna_players(self, ctx, online: bool = True, search: str = None, limit: int = 50):
        """Zeigt eine Liste der Spieler an."""
        params = {"online": str(online).lower(), "limit": limit}
        if search:
            params["search"] = search
            
        data, error = await self.api_request("/players", params)
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        if not data:
            await ctx.send("Keine Spieler gefunden.")
            return
        
        embed = discord.Embed(title="👥 Spielerliste", color=discord.Color.blue())
        description = ""
        for player in data[:20]:  # Max 20 im Embed
            name = player.get("name", "Unbekannt")
            uuid = player.get("id", "N/A")[:8]
            description += f"• **{name}** (`{uuid}...`)\n"
        
        if len(data) > 20:
            description += f"\n...und {len(data) - 20} weitere."
            
        embed.description = description or "Keine Spieler gefunden."
        await ctx.send(embed=embed)

    @luna_group.command(name="player")
    async def luna_player(self, ctx, player_id: str):
        """Zeigt Details zu einem bestimmten Spieler."""
        data, error = await self.api_request(f"/players/{player_id}")
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        embed = discord.Embed(title=f"👤 Spieler: {data.get('name', player_id)}", color=discord.Color.blue())
        embed.add_field(name="UUID", value=data.get("id", "N/A"), inline=False)
        embed.add_field(name="Erster Join", value=data.get("first_join", "N/A"), inline=True)
        embed.add_field(name="Letzter Join", value=data.get("last_join", "N/A"), inline=True)
        embed.add_field(name="Spielzeit", value=data.get("playtime", "N/A"), inline=True)
        embed.add_field(name="Bans", value=data.get("ban_count", 0), inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, active: bool = True):
        """Zeigt aktive oder alle Bans an."""
        params = {"active": str(active).lower()}
        data, error = await self.api_request("/bans", params)
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        if not data:
            await ctx.send("Keine Bans gefunden.")
            return
        
        embed = discord.Embed(title="🔨 Bans", color=discord.Color.red())
        description = ""
        for ban in data[:10]:  # Max 10 im Embed
            player = ban.get("player", {}).get("name", "Unbekannt")
            reason = ban.get("reason", "Kein Grund angegeben")
            description += f"• **{player}**: {reason}\n"
        
        if len(data) > 10:
            description += f"\n...und {len(data) - 10} weitere."
            
        embed.description = description or "Keine Bans gefunden."
        await ctx.send(embed=embed)

    @luna_group.command(name="cases")
    async def luna_cases(self, ctx, case_type: str = None):
        """Zeigt Fälle an (optional nach Typ filtern)."""
        params = {}
        if case_type:
            params["type"] = case_type
            
        data, error = await self.api_request("/cases", params)
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        if not data:
            await ctx.send("Keine Fälle gefunden.")
            return
        
        embed = discord.Embed(title="📁 Fälle", color=discord.Color.orange())
        description = ""
        for case in data[:10]:
            case_id = case.get("id", "N/A")
            case_type_val = case.get("type", "Unbekannt")
            description += f"• Fall **#{case_id}**: {case_type_val}\n"
        
        if len(data) > 10:
            description += f"\n...und {len(data) - 10} weitere."
            
        embed.description = description or "Keine Fälle gefunden."
        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """Zeigt die Mitarbeiterliste an."""
        data, error = await self.api_request("/staff")
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        if not data:
            await ctx.send("Keine Mitarbeiter gefunden.")
            return
        
        embed = discord.Embed(title="👮 Mitarbeiter", color=discord.Color.gold())
        description = ""
        for staff in data:
            name = staff.get("name", "Unbekannt")
            rank = staff.get("rank", "Unbekannt")
            description += f"• **{name}** - {rank}\n"
            
        embed.description = description or "Keine Mitarbeiter gefunden."
        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """Zeigt recente Absturzberichte an."""
        data, error = await self.api_request("/crashes")
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        if not data:
            await ctx.send("Keine Absturzberichte gefunden.")
            return
        
        embed = discord.Embed(title="💥 Absturzberichte", color=discord.Color.dark_red())
        description = ""
        for crash in data[:10]:
            crash_id = crash.get("id", "N/A")
            date = crash.get("date", "Unbekannt")
            description += f"• **#{crash_id}** am {date}\n"
        
        if len(data) > 10:
            description += f"\n...und {len(data) - 10} weitere."
            
        embed.description = description or "Keine Berichte gefunden."
        await ctx.send(embed=embed)

    @luna_group.group(name="set", invoke_without_command=True)
    @commands.is_owner()
    async def luna_set(self, ctx):
        """Konfiguriere den Luna Cog (Nur Bot-Owner)."""
        await ctx.send_help(ctx.command)

    @luna_set.command(name="token")
    @commands.is_owner()
    async def luna_set_token(self, ctx, token: str):
        """Setzt den API-Token."""
        await self.config.token.set(token)
        await ctx.send("✅ API-Token erfolgreich gesetzt!")

    @luna_set.command(name="url")
    @commands.is_owner()
    async def luna_set_url(self, ctx, url: str):
        """Setzt die Basis-URL der API."""
        await self.config.base_url.set(url)
        await ctx.send("✅ Basis-URL erfolgreich gesetzt!")
