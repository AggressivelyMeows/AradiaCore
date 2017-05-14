import discord
from AradiaCore import AradiaCore


class Bot(AradiaCore):
    def __init__(self):
        super().__init__()

    @AradiaCore.bot_owner
    async def cmd_owner(self,context):
        return await self.say('Hello, {context.author.name}. You are the bot owner!'.format(**locals()))

    async def cmd_test(self,context):
        em = discord.Embed(title='Links',colour=context.author.colour)
        em.add_field(name='Github',value='https://github.com/AggressivelyMeows/AradiaCore',inline=False)
        em.add_field(name='Website',value='http://aradiabot.me/')

        return await self.say("Hello, I am AradiaCore!\n**I am a bot framework made by Cerulean#7014 and made in python! Check out my links below!**",embed=em)

    async def cmd_meme(self, context):
        """
        Quick example command
        """
        em = discord.Embed(title='Memes')
        em.add_field(name=context.guild.name,value=context.author.name)
        return await self.say('', embed=em)

if __name__ == '__main__':
    aradiabot = Bot()
    aradiabot.boot()
