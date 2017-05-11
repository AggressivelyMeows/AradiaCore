import discord
from AradiaCore import aradiaCore


class bot(aradiaCore):
    def __init__(self):
        super().__init__()
    async def cmd_test(self,msg):
        return self.user.name
    async def cmd_meme(self,msg):
        """
        Quick example command
        """
        em = discord.Embed(title='Memes')
        await self.say('',embed=em)
        return None
if __name__ == '__main__':
    aradiabot = bot()
    aradiabot.boot()