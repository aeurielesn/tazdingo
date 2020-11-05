import asyncio
import discord
import io
import os
import re
import sqlite3
from asgiref.sync import sync_to_async
from datetime import timedelta
from django.utils import timezone
from utils import get_human_time, get_member_name, is_tuple, parse_time

# Django
from conf import settings
from data import models


ROBOT_FACE_EMOJI = '\N{ROBOT FACE}'
CROSS_MARK_EMOJI = '\N{CROSS MARK}'
SHIELD_EMOJI = '\N{SHIELD}'
ALERTS_DELAY = 60
TIMEDELTA_0 = timedelta(hours=0)
TIMEDELTA_1 = timedelta(hours=1)
TIMEDELTA_4 = timedelta(hours=4)
TIMEDELTA_8 = timedelta(hours=8)
TIMEDELTA_12 = timedelta(hours=12)
TIMEDELTA_24 = timedelta(hours=24)
DEFAULT_SHIELDS = set([4, 8, 12, 24])


class TazdingoPoach(object):
    def __init__(self):
        super(TazdingoPoach, self).__init__()
        self.shields = {}
        self.reins = {}
        self.preys = {}

    def load_from_db(self):
        for _shield in models.Shield.objects.all():
            self.shields[_shield.user_id] = _shield

        for _rein in models.Reinforcement.objects.all():
            self.reins[_rein.user_id] = _rein

        for _prey in models.Prey.objects.all():
            self.preys[_prey.prey_name] = _prey


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
        elif cmd == '$prune':
            if self._is_owner(message.author):
                await self._on_prune(message)
            else:
                await self._error(message)    
        elif cmd == '$track':
            if len(args) == 1:
                _prey_name = get_member_name(args[0], message.mentions)
                await self._on_track(message, prey_name=_prey_name)
            elif len(args):
                _prey_name = get_member_name(args[0], message.mentions)

                if is_tuple(args[1]):
                    _coords = args[1]
                    _shields = args[2:]
                else:
                    _coords = None 
                    _shields = args[1:]

                try:
                    _shields = set(map(int, _shields))
                except ValueError:
                    await self._error(message)    
                else:
                    await self._on_track(message, prey_name=_prey_name, coords=_coords, shields=_shields)
            else:
                await self._error(message)    
        elif cmd == '$lose':
            if len(args) == 1:
                _prey_name = get_member_name(args[0], message.mentions)
                await self._on_lose(message, prey_name=_prey_name)
            else:
                await self._error(message)
        elif cmd == '$tracks':
            await self._on_tracks(message)
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
  $prune  remove expired shields

Track commands:
  $tracks                                shows all tracks
  $track <who> [<x>,<y>] [<shields>...]  tracks a given set of shields
  $lose <who>                            stop tracking```"""
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
        _expired_notification = _expires < _now
        _expiring_notification = _elapsed < timedelta(hours=1)

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

    async def _on_prune(self, message):
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

    async def _lose(self, prey_name):
        _prey = self.poach.preys.pop(prey_name, None)
        if _prey:
            await sync_to_async(_prey.delete, thread_sensitive=True)()

    async def _on_track(self, message, prey_name, coords=None, shields=DEFAULT_SHIELDS):
        _four_notification = 4 not in shields
        _eight_notification = 8 not in shields
        _twelve_notification = 12 not in shields
        _twenty_four_notification = 24 not in shields

        if _four_notification and _eight_notification and _twelve_notification and _twenty_four_notification:
            await self._error(message)
        else:
            _now = timezone.now()
            _user_id = message.author.id

            _prey = models.Prey(
                user_id=_user_id,
                prey_name=prey_name,
                entered=_now,
                four_notification=_four_notification,
                eight_notification=_eight_notification,
                twelve_notification=_twelve_notification,
                twenty_four_notification=_twenty_four_notification,
            )

            if coords is not None:
                _prey.coords = coords

            await self._lose(prey_name)
            await sync_to_async(_prey.save, thread_sensitive=True)()
            self.poach.preys[_prey.prey_name] = _prey
            await self._ack(message)

    async def _on_lose(self, message, prey_name):
        if prey_name in self.poach.preys:
            await self._lose(prey_name)
            await self._ack(message)
        else:
            await self._error(message)

    async def _on_tracks(self, message):
        if self.poach.preys:
            _now = timezone.now()
            _expirations = []
            for _prey in self.poach.preys.values():
                if not _prey.four_notification and _prey.entered + TIMEDELTA_4 >= _now:
                    _expires = _prey.entered + TIMEDELTA_4
                elif not _prey.eight_notification and _prey.entered + TIMEDELTA_8 >= _now:
                    _expires = _prey.entered + TIMEDELTA_8
                elif not _prey.twelve_notification and _prey.entered + TIMEDELTA_12 >= _now:
                    _expires = _prey.entered + TIMEDELTA_12
                elif not _prey.twenty_four_notification and _prey.entered + TIMEDELTA_24 >= _now:
                    _expires = _prey.entered + TIMEDELTA_24
                else:
                    continue

                # print(_prey, _prey.entered, _expires, _prey.four_notification, _prey.eight_notification, _prey.twelve_notification, _prey.twenty_four_notification)
                _remaining = max(_expires - _now, TIMEDELTA_0)
                _expirations.append((_remaining, _prey))

            _formatted_message = io.StringIO()
            _formatted_message.write(f"Tracks:```")
            for _idx, (_remaining, _prey) in enumerate(sorted(_expirations, key=lambda _p: _p[0])):
                if _idx:
                    _formatted_message.write(f"\n")

                _human_time = get_human_time(_remaining)
                _formatted_message.write(f"{_human_time} {_prey.prey_name}")

            _formatted_message.write(f"```")
            await message.channel.send(_formatted_message.getvalue())
            await self._ack(message)
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

            _prey_mentions = []
            _expired_preys = []
            for _prey in self.poach.preys.values():
                _save = False
                _elapsed = _now - _prey.entered
                # print(_prey.prey_name, _elapsed, _prey.four_notification, _prey.eight_notification, _prey.twelve_notification, _prey.twenty_four_notification)
                if not _prey.twenty_four_notification and _elapsed >= TIMEDELTA_24:
                    _prey.four_notification = True
                    _prey.eight_notification = True
                    _prey.twelve_notification = True
                    _prey.twenty_four_notification = True
                    _what = "24"
                    _save = True
                elif not _prey.twelve_notification and _elapsed >= TIMEDELTA_12:
                    _prey.four_notification = True
                    _prey.eight_notification = True
                    _prey.twelve_notification = True
                    _what = "12"
                    _save = True
                elif not _prey.eight_notification and _elapsed >= TIMEDELTA_8:
                    _prey.four_notification = True
                    _prey.eight_notification = True
                    _what = "8"
                    _save = True
                elif not _prey.four_notification and _elapsed >= TIMEDELTA_4:
                    _prey.four_notification = True
                    _what = "4"
                    _save = True

                if _save:
                    if _prey.four_notification and _prey.eight_notification and _prey.twelve_notification and _prey.twenty_four_notification:
                        _expired_preys.append(_prey)
                    _prey_mentions.append((_prey, _what))
                    await sync_to_async(_prey.save, thread_sensitive=True)()

            for _prey, _what in _prey_mentions:
                await _channel.send(f"<@!{_prey.user_id}> {_prey.prey_name}'s {_what} hour shield may have expired!")

            for _prey in _expired_preys:
                self.poach.preys.pop(_prey.prey_name, None)
                await sync_to_async(_prey.delete, thread_sensitive=True)()

            await asyncio.sleep(ALERTS_DELAY)


client = TazdingoClient()
client.initialize()
client.run(settings.TAZDINGO_TOKEN)
