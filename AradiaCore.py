import json
import psutil
import discord
import asyncio
import logging
from attrdict import AttrDict

class aradiaCore(discord.Client):
    def __init__(self,*,prefix='!',autoDeleteResponse=True):
        self.prefix = prefix
        self.autoDelete = autoDeleteResponse
        super().__init__()
    async def upload(self,image):
        """
        Uploads to a defined channel
        returns the URL.
        """
        dest = self.config['uploadChannel']
        if not dest:
            raise EnvironmentError('Channel ID not selected. Please enter a upload channel id in config.json')
        channel = discord.utils.get(bot.get_all_channels(),id='307615051689361408')
        msg = await self.send_file(channel,image)
        return msg.attachments[0]['url']

    def save_json(self, filename, data):
        """Atomically saves json file - Will make directory if need be."""
        mypath = r'{}'.format(filename)
        rnd = randint(1000, 9999)
        path, ext = os.path.splitext(filename)
        tmp_file = "{}-{}.tmp".format(path, rnd)
        self._save_json(tmp_file, data)
        try:
            self._read_json(tmp_file)
        except json.decoder.JSONDecodeError:
            self.logger.exception("Attempted to write file {} but JSON "
                                    "integrity check on tmp file has failed. "
                                    "The original file is unaltered."
                                    "".format(filename))
            return False
        os.replace(tmp_file, filename)
        return True

    def load_json(self, filename):
        """Loads json file"""
        return self._read_json(filename)

    def is_valid_json(self, filename):
        """Verifies if json file exists / is readable"""
        try:
            self._read_json(filename)
            return True
        except FileNotFoundError:
            return False
        except json.decoder.JSONDecodeError:
            return False

    def _read_json(self, filename):
        with open(filename, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    def _save_json(self, filename, data):
        dir =filename.split('/')
        del dir[-1]
        dir = '/'.join(dir)
        if not os.path.exists(dir):
            directory = filename.split('/')
            del directory[-1]
            os.makedirs('/'.join(directory)) 
        with open(filename, encoding='utf-8', mode="w") as f:
            json.dump(data, f, indent=4,sort_keys=True,
                separators=(',',' : '))
        return data
    async def _wait_delete_msg(self, message, after):
        await asyncio.sleep(after)
        await self.delete_message(message)
    async def cmd_stats(self,msg):
        """
        Inbuilt command,
        Shows you stats of your bot.
        [Prefix]stats
        """
        toreturn = 'AradiaCore v3.5\n'
        toreturn += '------------\n'
        toreturn += 'Total servers: {}\n'.format(len(self.servers))
        toreturn += 'Total channels: {}\n'.format(len([x for x in self.get_all_channels()]))
        toreturn += '------------\n'
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss
        mem = float(mem)/1048576
        cpu = str(psutil.cpu_percent(interval=None)) + '%'
        toreturn += ':floppy_disk: | Memory usage: {}MB\n'.format(str(mem))
        toreturn += ':diamond_shape_with_a_dot_inside: | CPU usage: ' + cpu +'\n'
        return toreturn
    async def say(self,message,*,file=None,embed=None,tts=None,expire=0,dest=None):
        """
        Sends a message, tries to use the global context first but does have a `dest` fall back
        """
        if not dest:
            dest = self.context.channel
        message = message if message else ''
        msg = None
        if file:
            msg = await self.send_file(dest,file,content=message)
        else:
            msg = await self.send_message(dest,message,embed=embed,tts=tts)
        if expire and msg:
            asyncio.ensure_future(self._wait_delete_msg(msg,expire))
        return msg
    async def on_ready(self):
        toreturn = '{}\n'.format(self.user.name)
        toreturn += '------------\n'
        toreturn += 'Total servers: {}\n'.format(len(self.servers))
        toreturn += 'Total channels: {}\n'.format(len([x for x in self.get_all_channels()]))
        toreturn += '------------\n'
        toreturn += 'Running AradiaCore Version 0.5 - Public Alpha'
        print(toreturn)
    async def on_message(self,msg):
        if msg.author == self.user:
            return
        if not msg.content.startswith(self.prefix):
            return
        message_content = msg.content.strip()
        if msg.channel.is_private:
            return
        command, *args = message_content.split()
        command = command[len(self.prefix):].lower().strip()
        handler = getattr(self, 'cmd_%s' % command,None)
        if not handler:
            return
        res = None
        #Global Context
        #Holds info on current event.
        #Holds: Current message
        #-Message server
        #-Message channel 
        #-Message author
        #-Message embeds

        self.context = AttrDict({'msg':msg,
                   'server':msg.server,
                   'channel':msg.channel,
                   'author':msg.author,
                   'embed':msg.embeds})
    

        try:
            res = await handler(msg)
        except discord.errors.Forbidden:
            #If we cant talk, show message in console.
            print('[Error] Forbidden to talk in channel {}({}/{}({}))'.format(msg.channel.id,msg.channel.name,msg.server.name,msg.server.id))
            try:
                #PM user, if we cant, just ignore.
                await client.send_message(msg.author,'I cannot send a message in {}'.format(msg.channel.name))
            except discord.errors.Forbidden:
                print('Couldnt send forbidden message ;-; ')
        if res:
            try:
                if not isinstance(res,str):
                    sent = res
                else:
                    sent = await self.send_message(msg.channel,res)
            except discord.errors.Forbidden:
                sent = await self.send_message(msg.author,'I do not have permissions to run {} in {}({})'.format(handler.__name__[4:],msg.server.name,msg.channel.name))
        else:
            debug('{} Returned NoneType'.format(handler.__name__[4:]))
        return

    async def on_server_remove(s):
        debug('Left {}! Current total: {}'.format(s.name,len([x for x in self.servers])))
    async def on_server_join(s):
        debug('Joined {}! Current total: {}'.format(s.name,len([x for x in self.servers])))
    def boot(self):
        print('Booting...')
        try:
            config = self.load_json('config.json')
        except FileNotFoundError:
            raise ValueError('Config not found. Please read the github wiki for more info.')
        self.config = config
        try:
            self.run(config['token'])
        except discord.errors.LoginFailure:
            raise discord.errors.LoginFailure('Incorrect token. Please check ./config.json and make sure the "token" entry is correct. If you are still having issues, please go to the github wiki or join our server at: https://discord.gg/Sz2qQJt')
