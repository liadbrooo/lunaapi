from .lunadoc import LunaDoc

__red_enduser_data_statement__ = "Dieser Cog speichert keine persönlichen Daten von Endbenutzern."

def setup(bot):
    bot.add_cog(LunaDoc(bot))
