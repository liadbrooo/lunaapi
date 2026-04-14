from .lunadoc import LunaDoc

__red_version__ = "3.5.0"

async def setup(bot):
    await bot.add_cog(LunaDoc(bot))
