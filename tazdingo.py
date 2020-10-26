import asyncio
import discord
import io
import os
import re
import sqlite3
from asgiref.sync import sync_to_async
from datetime import timedelta
from django.utils import timezone
from utils import get_human_time, parse_time

# Django
from conf import settings
from data import models


ROBOT_FACE_EMOJI = '\N{ROBOT FACE}'
CROSS_MARK_EMOJI = '\N{CROSS MARK}'
SHIELD_EMOJI = '\N{SHIELD}'
ALERTS_DELAY = 60
TIMEDELTA_0 = timedelta(hours=0)
TIMEDELTA_1 = timedelta(hours=1)
TIME_RE = re.compile(r"\s*(?:(?P<days>\d+)\s*[dD])?\s*(?:(?P<hours>\d+)\s*[hH])?\s*(?:(?P<minutes>\d+)\s*[mM])?\s*(?:(?P<seconds>\d+)\s*[sS])?\s*")


class TazdingoPoach(object):
    def __init__(self):
        super(TazdingoPoach, self).__init__()
        self.shields = {}
        self.reins = {}

    def load_from_db(self):
        for _shield in models.Shield.objects.all():
            self.shields[_shield.user_id] = _shield

        for _rein in models.Reinforcement.objects.all():
            self.reins[_rein.user_id] = _rein


class TazdingoCommands(object):
    def __init__(self, poach=None):
        super(TazdingoCommands, self).__init__()
        self.poach = poach
        self.start_time = timezone.now()

    def _is_owner(self, user):
        if user.id == settings.OWNER:
            return True
        else:
            for r in user.roles:
                if settings.OWNERS_ROLE == r.id:
                    return True
        return False

    async def on_message(self, message):
        message_content = message.content.strip().split()
        if not message_content:
            return

        cmd, args = message_content[0].lower(), message_content[1:]

        if cmd == '$commands':
            await self._on_commands(message)
        elif cmd == '$hive':
            await self._on_hive(message)
        elif cmd == '$status':
            await self._on_status(message)
        elif cmd in ['$shield', "shield"]:
            if len(args) == 1:
                _seconds = parse_time(args[0])
                if _seconds is not None:
                    await self._on_shield(message, _seconds)
                else:
                    await self._error(message)
            else:
                await self._error(message)
        elif cmd == '$unshield':
            await self._on_unshield(message)
        elif cmd == '$rein':
            await self._on_rein(message)
        elif cmd == '$recall':
            await self._on_recall(message)
        elif cmd == '$notify':
            await self._on_notify(message)
        elif cmd == '$purge':
            if self._is_owner(message.author):
                await self._on_purge(message)
            else:
                await self._error(message)    
        elif cmd.startswith('$'):
            await self._error(message)

    async def _on_commands(self, message):
        available_commands = f"""```General commands:
  $commands  shows this message
  $status    shows bot status
  $hive      shows all shields/reins

Shield commands:
  $shield <hours>  set a shield
  $unshield        break a shield
  $notify          notifies all expired shields

Reinforcement commands:
  $rein    reinforce
  $recall  recall a reinforcement

Moderator commands:
  $purge  remove expired shields```"""
        await message.channel.send(available_commands)

    async def _ack(self, message, text=""):
        # await message.channel.send(text)
        await message.add_reaction(ROBOT_FACE_EMOJI)

    async def _error(self, message, text=""):
        # await message.channel.send(text)
        await message.add_reaction(CROSS_MARK_EMOJI)

    async def _on_status(self, message):
        _now = timezone.now()
        _up = get_human_time(_now - self.start_time)
        await message.channel.send(f"Taz'dingo! Ye-e-es!\n{_now} up {_up}")

    async def _on_hive(self, message):
        if self.poach.shields or self.poach.reins:
            if self.poach.shields:
                _now = timezone.now()
                _formatted_message = io.StringIO()
                _formatted_message.write(f"Shields:```")
                for _idx, _shield in enumerate(sorted(self.poach.shields.values(), key=lambda _s: _s.expires)):
                    if _idx:
                        _formatted_message.write(f"\n")

                    if _shield.expires < _now:
                        _human_time = "expired"
                    else:
                        _human_time = get_human_time(_shield.expires - _now)

                    _formatted_message.write(f"{_human_time} {_shield.display_name}")
                _formatted_message.write(f"```")
                await message.channel.send(_formatted_message.getvalue())

            if self.poach.reins:
                _formatted_message = io.StringIO()
                _formatted_message.write(f"Reins:```")
                for _idx, _rein in enumerate(self.poach.reins.values()):
                    if _idx:
                        _formatted_message.write(f"\n")

                    _formatted_message.write(f"{_rein.display_name}")
                _formatted_message.write(f"```")
                await message.channel.send(_formatted_message.getvalue())

            await self._ack(message)
        else:
            await self._error(message)

    async def _unshield(self, user_id):
        _shield = self.poach.shields.pop(user_id, None)
        if _shield:
            await sync_to_async(_shield.delete, thread_sensitive=True)()

    async def _on_shield(self, message, seconds):
        _now = timezone.now()
        _expires = _now + timedelta(seconds=seconds)
        _elapsed = _expires - _now
        _user_id = message.author.id
        _expired_notification = False  # _expires < _now
        _expiring_notification = False  # _elapsed < timedelta(hours=1)

        _shield = models.Shield(
          name=message.author.name,
          user_id=message.author.id,
          display_name=message.author.display_name,
          entered=_now,
          expires=_expires,
          expired_notification=_expired_notification,
          expiring_notification=_expiring_notification,
        )

        await self._unshield(_user_id)
        await self._recall(_user_id)
        await sync_to_async(_shield.save, thread_sensitive=True)()
        self.poach.shields[_shield.user_id] = _shield

        await self._ack(message, f"{message.author.mention} shield applied")

    async def _on_unshield(self, message):
        _user_id = message.author.id
        if _user_id in self.poach.shields:
            await self._unshield(_user_id)
            await self._ack(message, f"{message.author.mention} shield removed")
        else:
            await self._error(message, f"{message.author.mention} shield not found")

    async def _recall(self, user_id):
        _rein = self.poach.reins.pop(user_id, None)
        if _rein:
            await sync_to_async(_rein.delete, thread_sensitive=True)()

    async def _on_rein(self, message):
        _now = timezone.now()
        _user_id = message.author.id
        
        _rein = models.Reinforcement(
          name=message.author.name,
          user_id=message.author.id,
          display_name=message.author.display_name,
          entered=_now,
        )

        await self._unshield(_user_id)
        if _user_id not in self.poach.reins:
            await sync_to_async(_rein.save, thread_sensitive=True)()
        self.poach.reins[_rein.user_id] = _rein

        await self._ack(message, f"{message.author.mention} reinforcing")

    async def _on_recall(self, message):
        _user_id = message.author.id
        if _user_id in self.poach.reins:
            await self._recall(_user_id)
            await self._ack(message, f"{message.author.mention} recalling")
        else:
            await self._error(message, f"{message.author.mention} reinforcement not found")

    async def _on_notify(self, message):
        if self.poach.shields:
            _now = timezone.now()
            _expired_shields = [_shield for _shield in self.poach.shields.values() if _shield.expires < _now]
            if _expired_shields:
                _formatted_message = io.StringIO()
                for _idx, _shield in enumerate(_expired_shields):
                    if _idx:
                        _formatted_message.write(" ")

                    if _shield.expires < _now:
                        _formatted_message.write(f"<@!{_shield.user_id}>")

                _formatted_message.write(f" Hey! Your shield has expired!")
                await message.channel.send(_formatted_message.getvalue())
                await self._ack(message)
            else:
                await self._error(message)
        else:
            await self._error(message)

    async def _on_purge(self, message):
        if self.poach.shields:
            _now = timezone.now()
            _expired_shields = [_user_id for _user_id, _shield in self.poach.shields.items() if _shield.expires < _now]
            if _expired_shields:
                for _user_id in _expired_shields:
                    await self._unshield(_user_id)
                await self._ack(message)
            else:
                await self._error(message)
        else:
            await self._error(message)


class TazdingoClient(discord.Client):
    def __init__(self):
        super(TazdingoClient, self).__init__()
        self.poach = TazdingoPoach()
        self.commands = TazdingoCommands(self.poach)
        self.background_task = self.loop.create_task(self.notify_shield_state())

    def initialize(self):
        self.poach.load_from_db()
    
    async def on_ready(self):
        print(f'We have logged in as {self.user}')

    async def on_message(self, message):
        if message.channel.id != settings.SHIELDS_CHANNEL_ID:
            return

        if message.author == self.user:
            return

        await self.commands.on_message(message)

    async def notify_shield_state(self):
        await self.wait_until_ready()
        _channel = self.get_channel(settings.ALERTS_CHANNEL_ID)
        while not self.is_closed():
            _now = timezone.now()
            _expired_mentions = []
            _expiring_mentions = []

            for _shield in self.poach.shields.values():
                _remaining = _shield.expires - _now
                if not _shield.expired_notification and _remaining < TIMEDELTA_0:
                    _shield.expired_notification = True
                    _shield.expiring_notification = True
                    await sync_to_async(_shield.save, thread_sensitive=True)()
                    _expired_mentions.append(f"<@!{_shield.user_id}>")
                elif not _shield.expiring_notification and _remaining < TIMEDELTA_1:
                    _shield.expiring_notification = True
                    await sync_to_async(_shield.save, thread_sensitive=True)()
                    _expiring_mentions.append(f"<@!{_shield.user_id}>")

            if _expired_mentions:
                _mentions = " ".join(_expired_mentions)
                await _channel.send(f"{_mentions} Hey! Your shield has expired!")

            if _expiring_mentions:
                _mentions = " ".join(_expiring_mentions)
                await _channel.send(f"{_mentions} Hey! Your shield has almost expired!")

            await asyncio.sleep(ALERTS_DELAY)


client = TazdingoClient()
client.initialize()
client.run(settings.TAZDINGO_TOKEN)
