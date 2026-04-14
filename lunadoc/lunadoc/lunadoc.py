import aiohttp
import discord
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import box, pagify
from datetime import datetime

class LunaDoc(commands.Cog):
    """Interact with the Luna API documentation."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(
            api_token=None,
            base_url="https://api.lunadoc.example.com/api/public/v1"  # Standard-URL, anpassbar
        )
        self.session = None

    async def initialize(self):
        """Initialize the aiohttp session."""
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_api_headers(self):
        """Get headers for API requests including auth token if available."""
        token = await self.config.api_token()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def make_request(self, endpoint: str, params: dict = None):
        """Make a request to the Luna API."""
        base_url = await self.config.base_url()
        url = f"{base_url}{endpoint}"
        headers = await self.get_api_headers()
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    return {"error": "Unauthorized - Invalid or missing API token"}
                elif response.status == 404:
                    return {"error": "Resource not found"}
                else:
                    return {"error": f"API Error: {response.status}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.guild_only()
    async def luna_group(self, ctx):
        """Luna API interaction commands."""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Check the server status."""
        data = await self.make_request("/server/status")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return

        embed = discord.Embed(title="🖥️ Server Status", color=discord.Color.green())
        for key, value in data.items():
            embed.add_field(name=key.capitalize(), value=str(value), inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="players")
    async def luna_players(self, ctx, online: bool = None, search: str = None, limit: int = 50):
        """List players with optional filters."""
        params = {}
        if online is not None:
            params["online"] = str(online).lower()
        if search:
            params["search"] = search
        if limit:
            params["limit"] = min(limit, 100)
        
        data = await self.make_request("/players", params=params)
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No players found.")
            return

        embed = discord.Embed(title="👥 Players", color=discord.Color.blue())
        for player in data[:10]:  # Show max 10 players in embed
            name = player.get("name", "Unknown")
            status = "🟢 Online" if player.get("online") else "🔴 Offline"
            embed.add_field(name=name, value=status, inline=True)
        
        if len(data) > 10:
            embed.set_footer(text=f"... and {len(data) - 10} more players")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="player")
    async def luna_player(self, ctx, player_id: str):
        """Get details about a specific player."""
        data = await self.make_request(f"/players/{player_id}")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return

        embed = discord.Embed(title=f"👤 Player: {data.get('name', player_id)}", color=discord.Color.blue())
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = str(value)
            embed.add_field(name=key.capitalize(), value=str(value)[:1024], inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="playerbans")
    async def luna_playerbans(self, ctx, player_id: str):
        """Get bans for a specific player."""
        data = await self.make_request(f"/players/{player_id}/bans")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No bans found for this player.")
            return

        embed = discord.Embed(title=f"🚫 Bans for {player_id}", color=discord.Color.red())
        for ban in data[:5]:  # Show max 5 bans
            reason = ban.get("reason", "No reason")
            date = ban.get("date", "Unknown")
            embed.add_field(name=f"Ban on {date}", value=reason[:1024], inline=False)
        
        if len(data) > 5:
            embed.set_footer(text=f"... and {len(data) - 5} more bans")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="playercases")
    async def luna_playercases(self, ctx, player_id: str):
        """Get public cases for a specific player."""
        data = await self.make_request(f"/players/{player_id}/cases")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No public cases found for this player.")
            return

        embed = discord.Embed(title=f"📁 Cases for {player_id}", color=discord.Color.orange())
        for case in data[:5]:  # Show max 5 cases
            case_type = case.get("type", "Unknown")
            summary = case.get("summary", "No summary")
            embed.add_field(name=f"Case: {case_type}", value=summary[:1024], inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="playergamedata")
    async def luna_playergamedata(self, ctx, player_id: str, category: str):
        """Get game data for a specific player and category."""
        data = await self.make_request(f"/players/{player_id}/gamedata/{category}")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return

        embed = discord.Embed(title=f"🎮 Game Data: {category}", color=discord.Color.purple())
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = str(value)
            embed.add_field(name=key.capitalize(), value=str(value)[:1024], inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, active: bool = None):
        """List all bans with optional active filter."""
        params = {}
        if active is not None:
            params["active"] = str(active).lower()
        
        data = await self.make_request("/bans", params=params)
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No bans found.")
            return

        embed = discord.Embed(title="🚫 All Bans", color=discord.Color.red())
        for ban in data[:10]:  # Show max 10 bans
            player = ban.get("player", "Unknown")
            reason = ban.get("reason", "No reason")
            status = "🔴 Active" if ban.get("active") else "⚪ Inactive"
            embed.add_field(name=player, value=f"{reason[:50]}... - {status}", inline=True)
        
        if len(data) > 10:
            embed.set_footer(text=f"... and {len(data) - 10} more bans")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="cases")
    async def luna_cases(self, ctx, case_type: str = None):
        """List all cases with optional type filter."""
        params = {}
        if case_type:
            params["type"] = case_type
        
        data = await self.make_request("/cases", params=params)
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No cases found.")
            return

        embed = discord.Embed(title="📁 All Cases", color=discord.Color.orange())
        for case in data[:10]:  # Show max 10 cases
            case_type = case.get("type", "Unknown")
            summary = case.get("summary", "No summary")
            embed.add_field(name=case_type, value=summary[:100], inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """List all staff members."""
        data = await self.make_request("/staff")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No staff members found.")
            return

        embed = discord.Embed(title="👨‍💼 Staff Members", color=discord.Color.gold())
        for member in data:
            name = member.get("name", "Unknown")
            role = member.get("role", "No role")
            embed.add_field(name=name, value=role, inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata")
    async def luna_gamedata(self, ctx, category: str, search: str = None, limit: int = 50):
        """List game data entries for a category."""
        params = {}
        if search:
            params["search"] = search
        if limit:
            params["limit"] = min(limit, 100)
        
        data = await self.make_request(f"/gamedata/{category}", params=params)
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send(f"No game data found for category: {category}")
            return

        embed = discord.Embed(title=f"🎮 Game Data: {category}", color=discord.Color.purple())
        for entry in data[:10]:  # Show max 10 entries
            name = entry.get("name", "Unknown")
            description = entry.get("description", "No description")
            embed.add_field(name=name, value=description[:100], inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata-entry")
    async def luna_gamedata_entry(self, ctx, category: str, entry_id: str):
        """Get a specific game data entry."""
        data = await self.make_request(f"/gamedata/{category}/{entry_id}")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return

        embed = discord.Embed(title=f"🎮 Entry: {entry_id}", color=discord.Color.purple())
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = str(value)
            embed.add_field(name=key.capitalize(), value=str(value)[:1024], inline=False)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """List recent crash reports."""
        data = await self.make_request("/crashes")
        
        if "error" in data:
            await ctx.send(f"❌ {data['error']}")
            return
        
        if not data:
            await ctx.send("No crash reports found.")
            return

        embed = discord.Embed(title="💥 Recent Crashes", color=discord.Color.dark_red())
        for crash in data[:10]:  # Show max 10 crashes
            date = crash.get("date", "Unknown")
            error = crash.get("error", "No error message")
            embed.add_field(name=date, value=error[:100], inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.group(name="set")
    @checks.is_owner()
    async def luna_set_group(self, ctx):
        """Configure LunaDoc settings (Owner only)."""
        pass

    @luna_set_group.command(name="token")
    async def luna_set_token(self, ctx, token: str):
        """Set the API token for authentication."""
        await self.config.api_token.set(token)
        await ctx.send("✅ API token set successfully!")

    @luna_set_group.command(name="url")
    async def luna_set_url(self, ctx, url: str):
        """Set the base URL for the Luna API."""
        await self.config.base_url.set(url)
        await ctx.send(f"✅ Base URL set to: {url}")

    @luna_set_group.command(name="showconfig")
    async def luna_showconfig(self, ctx):
        """Show current configuration."""
        token = await self.config.api_token()
        url = await self.config.base_url()
        
        token_status = "✅ Set" if token else "❌ Not set"
        
        embed = discord.Embed(title="⚙️ LunaDoc Configuration", color=discord.Color.blue())
        embed.add_field(name="API Token", value=token_status, inline=True)
        embed.add_field(name="Base URL", value=url, inline=False)
        
        await ctx.send(embed=embed)
