# LunaDoc Cog Package

from .lunadoc import LunaDoc

__red_enduser_data_statement__ = "Dieser Cog speichert keine persistenten Benutzerdaten."


def setup(bot):
    bot.add_cog(LunaDoc(bot))
