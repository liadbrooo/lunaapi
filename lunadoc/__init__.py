"""LunaDoc - A Redbot cog for interacting with the Luna API."""

from .lunadoc import LunaDoc

__red_end_user_data_statement__ = "This cog does not store any end user data."


def setup(bot):
    """Load the LunaDoc cog."""
    bot.add_cog(LunaDoc(bot))
