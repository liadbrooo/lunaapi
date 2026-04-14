"""LunaDoc - Ein Redbot Cog für die Luna API."""
from .lunadoc import LunaDoc

__red_end_user_data_statement__ = "Speichert nur den API-Token und die Basis-URL lokal."

def setup(bot):
    """Lädt den LunaDoc Cog."""
    bot.add_cog(LunaDoc(bot))
