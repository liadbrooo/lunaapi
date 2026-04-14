"""
LunaDoc - A Redbot cog for interacting with the Luna API.

This cog provides commands to query server status, player information,
bans, cases, staff lists, game data, and crash reports from the Luna API.
"""

import aiohttp
import discord
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import box, pagify, escape


class LunaDoc(commands.Cog):
    """Interact with the Luna API."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=892847362847)
        
        # Default configuration
        default_global = {
            "api_token": None,
            "base_url": "https://api.luna.veryinsanee.space/api/public/v1"
        }
        self.config.register_global(**default_global)
        
        self.session = None

    async def initialize(self):
        """Initialize the aiohttp session."""
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self.session:
            await self.session.close()

    def cog_unload(self):
        """Handle cog unload."""
        if self.session:
            self.bot.loop.create_task(self.session.close())

    async def _make_request(self, endpoint: str, params: dict = None):
        """Make a request to the Luna API."""
        base_url = await self.config.base_url()
        token = await self.config.api_token()
        
        url = f"{base_url}{endpoint}"
        headers = {}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    return {"error": "Unauthorized - Invalid or missing API token"}
                elif response.status == 403:
                    return {"error": "Forbidden - You don't have permission to access this resource"}
                elif response.status == 404:
                    return {"error": "Not found"}
                else:
                    return {"error": f"API error: {response.status}"}
        except aiohttp.ClientError as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    @commands.group(name="luna", aliases=["lunadoc"])
    @commands.bot_has_permissions(embed_links=True)
    async def luna_group(self, ctx):
        """Luna API commands for querying server information."""
        pass

    @luna_group.command(name="status")
    async def luna_status(self, ctx):
        """Get the current server status."""
        await ctx.typing()
        result = await self._make_request("/server/status")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        embed = discord.Embed(
            title="🖥️ Luna Server Status",
            color=discord.Color.green() if result.get("online", False) else discord.Color.red()
        )
        
        for key, value in result.items():
            if isinstance(value, (bool, int, str)):
                embed.add_field(name=key.capitalize(), value=str(value), inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="players")
    async def luna_players(self, ctx, online: bool = None, search: str = None, limit: int = 50):
        """
        Get a list of players.
        
        Parameters:
        - online: Filter by online status (true/false)
        - search: Search by player name
        - limit: Maximum number of results (default: 50)
        """
        await ctx.typing()
        
        params = {}
        if online is not None:
            params["online"] = str(online).lower()
        if search:
            params["search"] = search
        params["limit"] = min(limit, 100)
        
        result = await self._make_request("/players", params)
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send("No players found.")
            return
        
        embed = discord.Embed(
            title=f"👥 Players ({len(result)})",
            color=discord.Color.blue()
        )
        
        # Display up to 10 players in the embed
        for player in result[:10]:
            name = player.get("name", "Unknown")
            player_id = player.get("id", "N/A")
            online_status = "🟢" if player.get("online", False) else "⚫"
            embed.add_field(name=f"{online_status} {escape(name)}", value=f"ID: `{player_id}`", inline=True)
        
        if len(result) > 10:
            embed.set_footer(text=f"Showing 10 of {len(result)} players. Use search for specific players.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="player")
    async def luna_player(self, ctx, player_id: str):
        """Get detailed information about a specific player."""
        await ctx.typing()
        result = await self._make_request(f"/players/{player_id}")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        embed = discord.Embed(
            title=f"👤 Player: {result.get('name', 'Unknown')}",
            color=discord.Color.blue()
        )
        
        for key, value in result.items():
            if key != "id" and isinstance(value, (bool, int, str)):
                embed.add_field(name=key.capitalize(), value=str(value)[:1024], inline=True)
        
        embed.set_footer(text=f"Player ID: {player_id}")
        await ctx.send(embed=embed)

    @luna_group.command(name="bans")
    async def luna_bans(self, ctx, active: bool = None):
        """
        Get ban information.
        
        Parameters:
        - active: Filter by active status (true/false)
        """
        await ctx.typing()
        
        params = {}
        if active is not None:
            params["active"] = str(active).lower()
        
        result = await self._make_request("/bans", params)
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send("No bans found.")
            return
        
        embed = discord.Embed(
            title=f"🔨 Bans ({len(result)})",
            color=discord.Color.red()
        )
        
        for ban in result[:10]:
            player_name = ban.get("player_name", "Unknown")
            reason = ban.get("reason", "No reason provided")
            banned_by = ban.get("banned_by", "Unknown")
            active_status = "🔴 Active" if ban.get("active", False) else "⚪ Inactive"
            
            embed.add_field(
                name=f"{escape(player_name)} - {active_status}",
                value=f"**Reason:** {escape(reason)[:100]}\n**By:** {escape(banned_by)}",
                inline=False
            )
        
        if len(result) > 10:
            embed.set_footer(text=f"Showing 10 of {len(result)} bans.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="cases")
    async def luna_cases(self, ctx, case_type: str = None):
        """
        Get case information.
        
        Parameters:
        - type: Filter by case type (e.g., violation)
        """
        await ctx.typing()
        
        params = {}
        if case_type:
            params["type"] = case_type
        
        result = await self._make_request("/cases", params)
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send("No cases found.")
            return
        
        embed = discord.Embed(
            title=f"📋 Cases ({len(result)})",
            color=discord.Color.orange()
        )
        
        for case in result[:10]:
            case_id = case.get("id", "N/A")
            case_type_val = case.get("type", "Unknown")
            player_name = case.get("player_name", "Unknown")
            
            embed.add_field(
                name=f"Case #{case_id} - {escape(case_type_val)}",
                value=f"**Player:** {escape(player_name)}",
                inline=False
            )
        
        if len(result) > 10:
            embed.set_footer(text=f"Showing 10 of {len(result)} cases.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="staff")
    async def luna_staff(self, ctx):
        """Get the list of staff members."""
        await ctx.typing()
        result = await self._make_request("/staff")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send("No staff members found.")
            return
        
        embed = discord.Embed(
            title="👮 Staff Members",
            color=discord.Color.gold()
        )
        
        for member in result:
            name = member.get("name", "Unknown")
            role = member.get("role", "Unknown")
            rank = member.get("rank", "N/A")
            
            embed.add_field(name=f"{escape(name)}", value=f"**Role:** {escape(role)}\n**Rank:** {escape(rank)}", inline=True)
        
        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata")
    async def luna_gamedata(self, ctx, category: str, search: str = None, limit: int = 50):
        """
        Get game data for a specific category.
        
        Parameters:
        - category: The data category to query
        - search: Search term
        - limit: Maximum results (default: 50)
        """
        await ctx.typing()
        
        params = {}
        if search:
            params["search"] = search
        params["limit"] = min(limit, 100)
        
        result = await self._make_request(f"/gamedata/{category}", params)
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send(f"No game data found for category: {category}")
            return
        
        embed = discord.Embed(
            title=f"🎮 Game Data: {category} ({len(result)})",
            color=discord.Color.purple()
        )
        
        for item in result[:10]:
            item_id = item.get("id", "N/A")
            name = item.get("name", "Unknown")
            
            embed.add_field(name=f"#{item_id} - {escape(name)}", value="Use `!luna gamedata-entry` for details", inline=True)
        
        if len(result) > 10:
            embed.set_footer(text=f"Showing 10 of {len(result)} entries.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="gamedata-entry")
    async def luna_gamedata_entry(self, ctx, category: str, entry_id: str):
        """Get a specific game data entry."""
        await ctx.typing()
        result = await self._make_request(f"/gamedata/{category}/{entry_id}")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        embed = discord.Embed(
            title=f"🎮 Game Data Entry: {category}",
            color=discord.Color.purple()
        )
        
        for key, value in result.items():
            if isinstance(value, (bool, int, str, list, dict)):
                value_str = str(value)[:1024]
                embed.add_field(name=key.capitalize(), value=value_str, inline=False)
        
        embed.set_footer(text=f"Entry ID: {entry_id}")
        await ctx.send(embed=embed)

    @luna_group.command(name="crashes")
    async def luna_crashes(self, ctx):
        """Get crash reports."""
        await ctx.typing()
        result = await self._make_request("/crashes")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send("No crash reports found.")
            return
        
        embed = discord.Embed(
            title=f"💥 Crash Reports ({len(result)})",
            color=discord.Color.dark_red()
        )
        
        for crash in result[:10]:
            crash_id = crash.get("id", "N/A")
            timestamp = crash.get("timestamp", "Unknown")
            player = crash.get("player", "Unknown")
            
            embed.add_field(
                name=f"Crash #{crash_id}",
                value=f"**Player:** {escape(player)}\n**Time:** {escape(str(timestamp))}",
                inline=False
            )
        
        if len(result) > 10:
            embed.set_footer(text=f"Showing 10 of {len(result)} reports.")
        
        await ctx.send(embed=embed)

    @luna_group.command(name="playerbans")
    async def luna_playerbans(self, ctx, player_id: str):
        """Get bans for a specific player."""
        await ctx.typing()
        result = await self._make_request(f"/players/{player_id}/bans")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send(f"No bans found for player {player_id}.")
            return
        
        embed = discord.Embed(
            title=f"🔨 Bans for Player {player_id}",
            color=discord.Color.red()
        )
        
        for ban in result:
            reason = ban.get("reason", "No reason provided")
            banned_by = ban.get("banned_by", "Unknown")
            active_status = "🔴 Active" if ban.get("active", False) else "⚪ Inactive"
            
            embed.add_field(
                name=f"{active_status}",
                value=f"**Reason:** {escape(reason)[:200]}\n**By:** {escape(banned_by)}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @luna_group.command(name="playercases")
    async def luna_playercases(self, ctx, player_id: str):
        """Get public cases for a specific player."""
        await ctx.typing()
        result = await self._make_request(f"/players/{player_id}/cases")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send(f"No public cases found for player {player_id}.")
            return
        
        embed = discord.Embed(
            title=f"📋 Cases for Player {player_id}",
            color=discord.Color.orange()
        )
        
        for case in result:
            case_id = case.get("id", "N/A")
            case_type = case.get("type", "Unknown")
            
            embed.add_field(
                name=f"Case #{case_id} - {escape(case_type)}",
                value="Public case record",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @luna_group.command(name="playergamedata")
    async def luna_playergamedata(self, ctx, player_id: str, category: str):
        """Get game data for a specific player and category."""
        await ctx.typing()
        result = await self._make_request(f"/players/{player_id}/gamedata/{category}")
        
        if "error" in result:
            await ctx.send(f"❌ {result['error']}")
            return
        
        if not result:
            await ctx.send(f"No game data found for player {player_id} in category {category}.")
            return
        
        embed = discord.Embed(
            title=f"🎮 Game Data for Player {player_id}",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Category: {category}")
        
        for key, value in result.items():
            if isinstance(value, (bool, int, str, list, dict)):
                value_str = str(value)[:1024]
                embed.add_field(name=key.capitalize(), value=value_str, inline=False)
        
        await ctx.send(embed=embed)

    # Configuration commands
    @luna_group.group(name="set")
    @checks.is_owner()
    async def luna_set_group(self, ctx):
        """Configure Luna API settings (Owner only)."""
        pass

    @luna_set_group.command(name="token")
    @checks.is_owner()
    async def luna_set_token(self, ctx, token: str):
        """Set the API authentication token."""
        await self.config.api_token.set(token)
        await ctx.send("✅ API token has been set successfully.")

    @luna_set_group.command(name="url")
    @checks.is_owner()
    async def luna_set_url(self, ctx, url: str):
        """Set the base API URL."""
        await self.config.base_url.set(url)
        await ctx.send(f"✅ Base URL has been set to: {url}")

    @luna_set_group.command(name="clear")
    @checks.is_owner()
    async def luna_set_clear(self, ctx):
        """Clear all Luna API settings."""
        await self.config.clear_all()
        await ctx.send("✅ All Luna API settings have been cleared.")
