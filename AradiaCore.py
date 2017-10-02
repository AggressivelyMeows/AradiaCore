import os
import psutil
import discord
import logging
import time
from random import randint
from datetime import datetime
import portalocker
import gc
from functools import wraps
from collections import namedtuple
from contextlib import contextmanager
import asyncio
try:
    import ujson as json
except ImportError:
    import json
try: 
    import uvloop
except ImportError:
    pass
else:
    print('0')
    #asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    # MUCH FASTER ASYNCIO EVENT LOOP. LINUX SERVER ONLY ;-;

Context = namedtuple("Context", "msg guild server channel author embed")

class Colours:
    """
    To use:
    >>> print(Colours.HEADER + 'boop' + Colours.ENDC)
    """
    HEADER = '\033[95m'  # Pink
    OKBLUE = '\033[94m'  # Blue
    OKGREEN = '\033[92m'  # Green!
    WARNING = '\033[93m'  # Red
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

Colors = Colours


class AradiaCore(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cooldown = {}
        self.counter = 0
        self.database = self.database()
        self.blockList = {}
        self.allCommands = {}
        self.commands = []
        self._commands = []
        self.config = self.database.load_json('config.json')
        self.backupContext = {}
        try:
            self.prefix = self.config['prefix']
        except KeyError: 
            print('No prefix found... using "!"')
            self.prefix = '!'
        try:
            self.autoDelete = self.config['autoRemove']
        except KeyError:
            self.autoDelete = False

        self.uploadchannel = None

        if self.config["uploadchannel"]:
            try:
                int(self.config["uploadchannel"])
            except ValueError:
                raise ValueError('Upload guild must be a ID')

        self.logger = logging.getLogger('discord')  # Discord Logging
        self.logger.setLevel(logging.INFO)
        self.handler = logging.FileHandler(filename=os.path.join('logs', 'discord.log'), encoding='utf-8', mode='w')
        self.handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(self.handler)

        self.internalLogger = logging.getLogger('internalAC')  # Internal Logging
        self.internalLogger.setLevel(logging.INFO)
        self.internalHandler = logging.FileHandler(filename=os.path.join('logs', 'aradiaCore.log'), encoding='utf-8', mode='w')
        self.internalHandler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.internalLogger.addHandler(self.handler)
    # utils
    def debug(self,string):
        """
        Allows you to log special stuff to the console as well as to the log.
        """
        print(Colours.WARNING + string + Colours.ENDC)
        if not self.devMode:
            em = discord.Embed(description=string,colour=discord.Color.orange())
            x = '`[{}]` :information_source: Info'.format(str(datetime.utcnow()))
            asyncio.ensure_future(self.get_channel(343206548568277002).send(x,embed=em))
    def makeProfile(self,user):
        profile = {
            'name':user.name,'id':str(user.id),
            'desc':'I am a spoopy ghost! (No desc set yet!)',
            'extra':'Extra',
            'feed':[],
            'likes':0,
            'dislikes':0,
            'reports':[],
            'colour':'#FFF' ,
            'views':0,
            'badges':[],
            'settings':{},
            'followers':[],
            'reports':[],
            'blocked':[]}
        aradiabot.database.save_json('profiles/{}/profile.json'.format(user.id),profile)
        return profile
    def load_profile(self,member):
        """
        Loads a users profile, returns {} if none found.
        """
        return self.database.load_json('profiles/{}/profile.json'.format(member)) if self.database.is_valid_json('profiles/{}/profile.json'.format(member)) else self.makeProfile(member)
    async def upload(self, image):
        """
        Uploads to a defined guild
        returns the URL.
        """
        dest = self.config['uploadchannel']
        if not dest:
            raise EnvironmentError('guild ID not selected. Please enter a upload guild id in config.json')

        msg = await self.uploadchannel.send(file=discord.File(image))
        return msg.attachments[0]['url']

    async def cmd_stats(self,msg):
        """{"title":"Stats","how2use":">stats"}
        Inbuilt command,
        Shows you stats of your bot.
        [Prefix]stats
        """
        r = await self.http._session.get('https://srhpyqt94yxb.statuspage.io/api/v1/summary.json')
        r = await r.json()

        toreturn = 'AradiaCore v3.5\n'
        toreturn += '------------\n'
        toreturn += 'Total guilds: {}\n'.format(len(self.guilds))
        toreturn += '------------\n'
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss
        mem = float(mem)/1048576
        cpu = str(psutil.cpu_percent(interval=None)) + '%'
        toreturn += ':floppy_disk: | Memory usage: {}MB\n'.format(str(mem))
        toreturn += ':diamond_shape_with_a_dot_inside: | CPU usage: ' + cpu +'\n'
        em = discord.Embed(title='Discord server stats',description=r['status']['description'],colour=discord.Color.blurple())
        for server in reversed(sorted(r['components'],key= lambda s: s['position'])):
            status = '✔ Online - ' if server['status'] == 'operational' else '❌ Error - '
            if not server.get('description'): v =  'No problems' if server['status'] == 'operational' else 'Theres an error'
            else:v = server['description']
            inline = True
            em.add_field(name=status + ' ' +server['name'],value=v,inline=inline)
        return await self.say(toreturn,embed=em)

    async def say(self, message, *, file=None, embed=None, tts=None, expire=0, dest=None):
        """
        Sends a message, tries to use the global context first but does have a `dest` fall back
        """
        if not dest:
            dest = self.context.channel
        
        message = message if message else ''

        msg = await dest.send(message,embed=embed,tts=tts, file=file if file else None, **({"delete_after": expire} if expire else {}))
        return msg

    def arg_check(args):
        try: args[0]
        except IndexError: return None
        else: return args
    async def on_ready(self):
        toreturn = '{}\n'.format(self.user.name)
        toreturn += '------------\n'
        toreturn += 'Total guilds: {}\n'.format(len(self.guilds))
        toreturn += '------------\n'
        toreturn += 'Prefix: {}\n'.format(self.config['prefix'])
        toreturn += 'Running AradiaCore Version 1.0'
        print(toreturn)
        if self.is_live:
            self.prefix = '>'
        else:
            self.prefix == '>>'
        
        self.uploadchannel = discord.utils.get(self.get_all_channels(), id=self.config["uploadchannel"])
        await self.ready() # Pass to user for ready function
        print('Finished startup.')
    async def ready(self):
        return
    
    def load_guild_settings(self,guild,override=False):
        if not self.devMode or override:
            
            return self.database.load_json('servers/{}/settings.json'.format(guild.id)) if self.database.is_valid_json('servers/{}/settings.json'.format(guild.id)) else {}
        return {}
    async def new_message(self,msg):
        return
    async def on_message(self, msg):
        
        if msg.author.id == 210695770217644032 and 'BOTSPLODE' in msg.content:
            await msg.channel.send('Poor 72... *pap* ;w;')

        if not self.is_ready:
            return 
        self.loop.create_task(self.new_message(msg))
        if self.devMode and msg.author.id != 190092287722651648:
            return
        if msg.author.bot:
            return

        if msg.guild is None:
            return
        if not msg.content.startswith(self.prefix):
            return

        config = self.load_guild_settings(msg.guild)
        if config:
            if config['enabled'] and config['mutedChannels']:
                if msg.channel.id in config['mutedChannels'] and not [x for x in config['modRoles'] if x in [x.id for x in msg.author.roles]]:
                    return
        message_content = msg.content.strip()
        command, *args = message_content.split()
        command = command[len(self.prefix):].lower().strip()
        handler = getattr(self, 'cmd_%s' % command, None)
        if not handler:
            return
        self.debug('[Command - Start] {} started.'.format(command))
        res = None

        # Global Context
        # Holds info on current event.
        # Holds: Current message
        # -Message server
        # -Message guild
        # -Message author
        # -Message embeds

        self.context = Context(**{'msg': msg,
                                  'guild': msg.guild,
                                  'server': msg.guild,
                                  'channel': msg.channel,
                                  'author': msg.author,
                                  'embed': msg.embeds})
        timeBefore = time.time()
        try:
            if not isinstance(handler,Command):
                res = await handler(self.context)
            else:
                res = await handler.run(self,self.context)

        except discord.errors.Forbidden:
            # If we cant talk, show message in console.
            print('[Error] Forbidden to talk in guild {}({}/{})'.format(msg.guild.id, msg.guild.name, msg.guild.id))
            try:
                # PM user, if we cant, just ignore.
                await msg.author.send('Err: I got a discord.Forbidden error!\nThis could be because I dont have permissions to talk or another permission is missing.\nGuild: {}'.format(msg.guild.name))
            except discord.errors.Forbidden:
                print('Couldnt send forbidden message ;-; ')
        timeTaken = time.time() - timeBefore
        sent = None
        if res:
            try:
                if not isinstance(res, str):
                    sent = res
                else:
                    sent = await msg.channel.send(res)
            except discord.errors.Forbidden:
                    sent = await msg.author.send('Err: I got a discord.Forbidden error!\nThis could be because I dont have permissions to talk or another permission is missing.\nGuild: {}'.format(msg.guild.name))
        if len(self._commands) <= 50:
            self._commands.append((msg.id, sent.id))
        else:
            del self._commands[-1]
            self._commands.append((msg.id, sent.id))
        self.debug('[Command - Finish {}s] {} used {} in {}/{}'.format('%.3f' % float(timeTaken),str(msg.author),command,str(msg.guild),str(msg.channel)))
        gc.collect()
        self.loop.create_task(self._count_message())
        return
    async def _count_message(self):
        self.counter += 1
        await asyncio.sleep(60)
        self.counter -=1
    async def on_message_delete(self, msg):
        if self.autoDelete:
            chmsg = [x for x in self._commands if x[0] == msg.id]
            if chmsg:
                orig, sent = chmsg[0]
                try:
                    await sent.delete()
                except discord.errors.NotFound:
                    pass
                except discord.errors.Forbidden:
                    pass
                del self._commands[self._commands.index(chmsg[0])]
                self.debug('Removed {} from messages list'.format(sent.id))

    async def on_guild_remove(self, s):
        self.debug('Left {}! Current total: {}'.format(s.name, len(self.guilds)))

    async def on_guild_join(self, s):
        self.debug('Joined {}! Current total: {}'.format(s.name, len(self.guilds)))

    def boot(self):
        print('Booting...')
        try:
            config = self.database.load_json('config.json')
        except FileNotFoundError:
            raise ValueError('Config not found. Please read the github wiki for more info.')
        self.config = config
        try:
            self.run(config['token'])
        except discord.errors.LoginFailure:
            print(Colours.WARNING + 'Incorrect token.\n'
                                    'Please check ./config.json and make sure the "token" entry is correct.\n'
                                    'If you are still having issues, please go to the github wiki or join our server at:\n'
                                    'https://discord.gg/Sz2qQJt' + Colours.ENDC)

    # Permission related wrappers
    @staticmethod
    def bot_owner(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            async def error(error, *, user=None):
                print('Error: {} attempted bot owner command.'.format(user if user is not None else 'User'))
                return error
            ctx = args[1]
            if ctx.author.id != args[0].config['owner']:
                return error('This command is locked to the bot owner only.', user=ctx.author.name)
            return f(*args, **kwargs)
        return wrapper

    class database:
        # Custom database handler.
        @classmethod
        def save_json(cls, filename, data):
            """Atomically saves json file - Will make directory if need be. NOT ASYNC.
            BEAWARE: this is not very good for concurency
            """
            mypath = r'{}'.format(filename)
            rnd = randint(1000, 9999)
            path, ext = os.path.splitext(filename)
            tmp_file = "{}-{}.tmp".format(path, rnd)
            cls._save_json(tmp_file, data)
            try:
                cls._read_json(tmp_file)
            except json.decoder.JSONDecodeError:
                logging.exception("Attempted to write file {} but JSON "
                                      "integrity check on tmp file has failed. "
                                      "The original file is unaltered."
                                      "".format(filename))
                return False
            while 1: # Save while block so we can ensure saving
                try: 
                    os.replace(tmp_file, filename)
                    break
                except PermissionError:
                    print('Failed saving json, waiting...')
                    time.sleep(0.1)
            return True

        @classmethod
        def load_json(cls, filename):
            """Loads json file"""
            return cls._read_json(filename)

        def is_valid_json(cls, filename):
            """Verifies if json file exists / is readable"""
            try:
                cls._read_json(filename)
                return True
            except FileNotFoundError:
                return False
            except json.decoder.JSONDecodeError:
                return False

        @staticmethod
        def _read_json(filename):
            with open(filename, encoding='utf-8', mode="r") as f:
                data = json.load(f)
            return data

        @staticmethod
        def _save_json(filename, data):
            dir = filename.split('/')
            del dir[-1]
            dir = '/'.join(dir)
            if not os.path.exists(dir):
                directory = filename.split('/')
                del directory[-1]
                os.makedirs('/'.join(directory))
            x = True
            while x:
                if os.path.exists(filename +'.lock'):
                    asyncio.ensure_future(asyncio.sleep(0.5))
                else:
                    break
            
            with open(filename, encoding='utf-8', mode="w") as f:
                portalocker.lock(f,portalocker.LOCK_EX)
                json.dump(data, f, indent=4, sort_keys=True,
                          separators=(',', ' : '))
                portalocker.unlock(f)
            return data
    
    def command(name=None,**kwargs):
        def deco(function):
            return Command(name=function.__name__[:4] if not name else name,func=function,**kwargs)
        return deco
class Command():
    # If people want a more "EXT" style command system, we support it
    def __init__(self,name,func, **kwargs):
        self.name=name
        self.help = kwargs.get('help',None)
        self.run = func

if __name__ == '__main__':
    print('This framework is designed to be run inside another script. Try importing.')
