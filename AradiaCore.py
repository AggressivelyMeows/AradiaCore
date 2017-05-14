import os
import psutil
import discord
import logging
from random import randint
from functools import wraps
from collections import namedtuple

try:
    import ujson as json
except ImportError:
    import json

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
        self._messages = []
        self.config = self.json.load_json('config.json')
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
        self.handler = logging.FileHandler(filename=os.path.join('resources', 'discord.log'), encoding='utf-8', mode='w')
        self.handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(self.handler)

    # utils
    @staticmethod
    def debug(string):
        """
        Allows you to log special stuff to the console as well as to the log.
        """
        print(Colours.WARNING + string + Colours.ENDC)
    
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
        """
        Inbuilt command,
        Shows you stats of your bot.
        [Prefix]stats
        """
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
        return toreturn

    async def say(self, message, *, file=None, embed=None, tts=None, expire=0, dest=None):
        """
        Sends a message, tries to use the global context first but does have a `dest` fall back
        """
        if not dest:
            dest = self.context.channel

        message = message if message else ''

        msg = await dest.send(message, file=discord.File(file) if file else None, **({"delete_after": expire} if expire else {}))
        return msg

    async def on_ready(self):
        toreturn = '{}\n'.format(self.user.name)
        toreturn += '------------\n'
        toreturn += 'Total guilds: {}\n'.format(len(self.guilds))
        toreturn += '------------\n'
        toreturn += 'Prefix: {}\n'.format(self.config['prefix'])
        toreturn += 'Running AradiaCore Version 0.7 - Public Alpha'
        print(toreturn)
        self.uploadchannel = discord.utils.get(self.get_all_channels(), id=self.config["uploadchannel"])

    async def on_message(self, msg):
        if msg.author.bot:
            return

        if msg.guild is None:
            return

        if not msg.content.startswith(self.prefix):
            return

        message_content = msg.content.strip()
        command, *args = message_content.split()
        command = command[len(self.prefix):].lower().strip()
        handler = getattr(self, 'cmd_%s' % command, None)
        if not handler:
            return

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

        try:
            res = await handler(self.context)

        except discord.errors.Forbidden:
            # If we cant talk, show message in console.
            print('[Error] Forbidden to talk in guild {}({}/{}({}))'.format(msg.guild.id, msg.guild.name, msg.server.name, msg.server.id))
            try:
                # PM user, if we cant, just ignore.
                await msg.author.send('I cannot send a message in {}'.format(msg.guild.name))
            except discord.errors.Forbidden:
                print('Couldnt send forbidden message ;-; ')

        sent = None
        if res:
            try:
                if not isinstance(res, str):
                    sent = res
                else:
                    sent = await msg.channel.send(res)
            except discord.errors.Forbidden:
                sent = await msg.author.send('I do not have permissions to run {} in {}({})'.format(handler.__name__[4:], msg.server.name,msg.guild.name))

        self._messages.append((msg, sent))
        return

    async def on_message_delete(self, msg):
        if self.autoDelete:
            chmsg = [x for x in self._messages if x[0].id == msg.id]
            if chmsg:
                orig, sent = chmsg[0]
                try:
                    await sent.delete()
                except discord.errors.NotFound:
                    pass
                except discord.errors.Forbidden:
                    pass
                del self._messages[self._messages.index(chmsg[0])]
                self.debug('Removed {} from messages list'.format(sent.id))

    async def on_server_remove(self, s):
        self.debug('Left {}! Current total: {}'.format(s.name, len(self.guilds)))

    async def on_server_join(self, s):
        self.debug('Joined {}! Current total: {}'.format(s.name, len(self.guilds)))

    def boot(self):
        print('Booting...')
        try:
            config = self.json.load_json('config.json')
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

    class json:
        # Json related functions
        @classmethod
        def save_json(cls, filename, data):
            """Atomically saves json file - Will make directory if need be."""
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
            os.replace(tmp_file, filename)
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
            with open(filename, encoding='utf-8', mode="w") as f:
                json.dump(data, f, indent=4, sort_keys=True,
                          separators=(',', ' : '))
            return data


if __name__ == '__main__':
    print('This framework is designed to be run inside another script. Try importing.')
