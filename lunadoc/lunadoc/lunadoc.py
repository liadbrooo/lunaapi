from redbot.core import commands
from redbot.core.bot import Red
from redbot.core import checks
import discord
from discord.ext import commands as dcommands
import aiohttp
import asyncio

class LunaDoc(commands.Cog):
    """Ein Cog zur Interaktion mit der Luna API."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.base_url = "https://api.luna.veryinsanee.space/api/public/v1"
        self.token = None

    async def api_request(self, endpoint: str, params: dict = None):
        """Führt eine API-Anfrage durch und gibt die rohen Daten zurück."""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        return {"_error": f"API-Fehler: Status {response.status}"}
                    
                    try:
                        data = await response.json()
                    except Exception:
                        return {"_error": "Ungültige JSON-Antwort von der API"}

                    # Extrahiere die eigentlichen Daten aus der Antwort
                    if isinstance(data, dict):
                        # Prüfe auf Fehler zuerst
                        if "error" in data and "data" not in data:
                            return {"_error": data["error"]}
                        
                        # Verschiedene mögliche Schlüssel für die Daten
                        for key in ["data", "result", "response", "players", "bans", "cases", "staff", "crashes"]:
                            if key in data:
                                result = data[key]
                                if isinstance(result, dict) and "error" in result:
                                    return {"_error": result["error"]}
                                return result
                        
                        if "error" in data:
                            return {"_error": data["error"]}
                        
                        return data
                    
                    return data
                
        except aiohttp.ClientConnectorError:
            return {"_error": "Verbindung zur API fehlgeschlagen. DNS oder Netzwerkproblem."}
        except asyncio.TimeoutError:
            return {"_error": "API-Request Timeout."}
        except Exception as e:
            return {"_error": f"Unbekannter Fehler: {str(e)}"}

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.guild_only()
    async def luna_group(self, ctx):
        """Befehlsgruppe für Luna-API-Abfragen."""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Zeigt den Serverstatus der Luna API an."""
        data = await self.api_request("server/status")

        if isinstance(data, dict) and "_error" in data:
            embed = discord.Embed(title="❌ Fehler", description=data["_error"], color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title="🟢 Luna Server Status", color=discord.Color.green())
        embed.set_footer(text=f"Angefragt von {ctx.author.name}", icon_url=ctx.author.display_avatar.url)

        if isinstance(data, dict):
            for key, value in data.items():
                display_value = str(value)[:1000]
                embed.add_field(name=key.title(), value=display_value or "N/A", inline=True)
        else:
            embed.description = str(data)[:2000]

        await ctx.send(embed=embed)

    @luna_group.command(name="players")
    async def luna_players(self, ctx, online: bool = False, *, search: str = None):
        """Zeigt eine Liste der Spieler an."""
        params = {"limit": "50"}
        if online:
            params["online"] = "true"
        if search:
            params["search"] = search

        data = await self.api_request("players", params)

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if not data or (isinstance(data, list) and len(data) == 0):
            await ctx.send("ℹ️ Keine Spieler gefunden.")
            return

        if not isinstance(data, list):
            data = [data]

        embed = discord.Embed(title="🎮 Spielerliste", color=discord.Color.blue(), description=f"Gefunden: {len(data)} Spieler")

        for player in data[:10]:
            if not isinstance(player, dict):
                continue
            name = player.get("name", player.get("username", "Unbekannt"))
            uuid = player.get("id", player.get("uuid", "N/A"))
            online_status = "🟢" if player.get("online", False) else "⚫"
            embed.add_field(name=f"{online_status} {name}", value=f"ID: `{uuid}`", inline=False)

        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Spieler.")

        await ctx.send(embed=embed)

    @luna_group.command(name="player")
    async def luna_player(self, ctx, player_id: str):
        """Zeigt Details zu einem spezifischen Spieler an."""
        data = await self.api_request(f"players/{player_id}")

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if not data or (isinstance(data, dict) and "error" in data):
            await ctx.send("ℹ️ Spieler nicht gefunden.")
            return

        embed = discord.Embed(title=f"👤 Spieler: {data.get('name', 'Unbekannt')}", color=discord.Color.blue())
        embed.add_field(name="ID", value=data.get("id", data.get("uuid", "N/A")), inline=True)
        embed.add_field(name="Name", value=data.get("name", "N/A"), inline=True)

        extra_fields = ["online", "firstJoin", "lastJoin", "playTime"]
        for field in extra_fields:
            if field in data:
                embed.add_field(name=field.title(), value=str(data[field]), inline=False)

        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, active: bool = True):
        """Zeigt die Bans an."""
        params = {"active": "true" if active else "false"}
        data = await self.api_request("bans", params)

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if not data or (isinstance(data, list) and len(data) == 0):
            status = "aktive" if active else "inaktive"
            await ctx.send(f"ℹ️ Keine {status} Bans gefunden.")
            return

        if not isinstance(data, list):
            data = [data]

        embed = discord.Embed(title=f"{'🔴 Aktive' if active else '⚪ Inaktive'} Bans", color=discord.Color.red(), description=f"Gefunden: {len(data)} Bans")

        for ban in data[:10]:
            if not isinstance(ban, dict):
                continue
            player_info = ban.get("player", {})
            if isinstance(player_info, dict):
                player_name = player_info.get("name", "Unbekannt")
            else:
                player_name = str(player_info) if player_info else "Unbekannt"

            reason = ban.get("reason", "Kein Grund angegeben")
            banned_by = ban.get("bannedBy", "Unbekannt")
            date = ban.get("date", ban.get("created", "N/A"))

            value = f"**Grund:** {reason[:100]}\n**Von:** {banned_by}\n**Datum:** {date}"
            embed.add_field(name=player_name, value=value, inline=False)

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

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if not data or (isinstance(data, list) and len(data) == 0):
            msg = "Keine Fälle gefunden."
            if case_type:
                msg = f"Keine Fälle vom Typ '{case_type}' gefunden."
            await ctx.send(f"ℹ️ {msg}")
            return

        if not isinstance(data, list):
            data = [data]

        embed = discord.Embed(title="📁 Fälle", color=discord.Color.orange(), description=f"Gefunden: {len(data)} Fälle")

        for case in data[:10]:
            if not isinstance(case, dict):
                continue
            case_id = case.get("id", "N/A")
            case_type_val = case.get("type", "Unbekannt")
            player = case.get("player", {})
            player_name = player.get("name", "Unbekannt") if isinstance(player, dict) else str(player)

            value = f"**Typ:** {case_type_val}\n**Spieler:** {player_name}"
            embed.add_field(name=f"Fall #{case_id}", value=value, inline=False)

        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Fälle.")

        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """Zeigt die Mitarbeiterliste an."""
        data = await self.api_request("staff")

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if isinstance(data, dict):
            for key in ["staff", "members", "data", "result"]:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]

        if not data or (isinstance(data, list) and len(data) == 0):
            await ctx.send("ℹ️ Keine Mitarbeiter gefunden.")
            return

        if not isinstance(data, list):
            data = [data]

        embed = discord.Embed(title="👥 Mitarbeiter", color=discord.Color.gold(), description=f"Insgesamt: {len(data)}")

        for member in data:
            if not isinstance(member, dict):
                embed.add_field(name=str(member), value="Mitarbeiter", inline=False)
                continue

            name = member.get("name", member.get("username", "Unbekannt"))
            role = member.get("role", member.get("rank", "N/A"))
            permissions = member.get("permissions", [])

            value = f"**Rolle:** {role}"
            if permissions:
                perm_list = ", ".join(permissions[:5]) if isinstance(permissions, list) else str(permissions)
                value += f"\n**Rechte:** {perm_list}"

            embed.add_field(name=name, value=value, inline=False)

        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata")
    async def luna_gamedata(self, ctx, category: str, *, search: str = None):
        """Zeigt Spieldaten für eine Kategorie an."""
        params = {"limit": "50"}
        if search:
            params["search"] = search

        data = await self.api_request(f"gamedata/{category}", params)

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if not data or (isinstance(data, list) and len(data) == 0):
            await ctx.send(f"ℹ️ Keine Spieldaten für Kategorie '{category}' gefunden.")
            return

        if not isinstance(data, list):
            data = [data]

        embed = discord.Embed(title=f"🎲 Spieldaten: {category}", color=discord.Color.purple(), description=f"Gefunden: {len(data)} Einträge")

        for entry in data[:10]:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id", "N/A")
            name = entry.get("name", "Unbekannt")

            extra = []
            if "value" in entry:
                extra.append(f"Wert: {entry['value']}")
            if "description" in entry:
                extra.append(entry["description"][:50])

            value = f"ID: `{entry_id}`"
            if extra:
                value += "\n" + " | ".join(extra)

            embed.add_field(name=name, value=value, inline=False)

        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Einträge.")

        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """Zeigt die neuesten Absturzberichte an."""
        data = await self.api_request("crashes")

        if isinstance(data, dict) and "_error" in data:
            await ctx.send(f"❌ Fehler: {data['_error']}")
            return

        if not data or (isinstance(data, list) and len(data) == 0):
            await ctx.send("ℹ️ Keine Absturzberichte gefunden.")
            return

        if not isinstance(data, list):
            data = [data]

        embed = discord.Embed(title="💥 Absturzberichte", color=discord.Color.dark_grey(), description=f"Insgesamt: {len(data)} Berichte")

        for crash in data[:10]:
            if not isinstance(crash, dict):
                continue
            crash_id = crash.get("id", "N/A")
            timestamp = crash.get("timestamp", crash.get("date", crash.get("created", "N/A")))
            server = crash.get("server", "Unbekannt")
            error_type = crash.get("errorType", crash.get("type", "Unbekannt"))

            value = f"**Zeit:** {timestamp}\n**Server:** {server}\n**Typ:** {error_type}"
            embed.add_field(name=f"Crash #{crash_id}", value=value, inline=False)

        if len(data) > 10:
            embed.set_footer(text=f"... und {len(data) - 10} weitere Berichte.")

        await ctx.send(embed=embed)

    @luna_group.command(name="set")
    @checks.is_owner()
    async def luna_set(self, ctx, setting: str, *, value: str):
        """Setzt Konfigurationseinstellungen (nur Bot-Besitzer)."""
        if setting.lower() == "token":
            self.token = value
            await ctx.send("✅ API-Token wurde gesetzt.")
        elif setting.lower() == "url":
            self.base_url = value
            await ctx.send("✅ API-Basis-URL wurde gesetzt.")
        else:
            await ctx.send("❌ Ungültige Einstellung. Verfügbare Einstellungen: `token`, `url`.")


async def setup(bot: Red):
    await bot.add_cog(LunaDoc(bot))
