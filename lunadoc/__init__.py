from .lunadoc.lunadoc import LunaDoc

__red_enduser_data_statement__ = "Dieser Cog speichert keine persönlichen Daten von Endbenutzern."

async def setup(bot):
    await bot.add_cog(LunaDoc(bot))
