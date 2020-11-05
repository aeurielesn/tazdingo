import io
import re


COMPLEX_TIME_RE = re.compile(r"^(?:(?P<days>\d+)\s*(d|D|day|days))?\s*(?:(?P<hours>\d+)\s*(h|H|hour|hours))?\s*(?:(?P<minutes>\d+)\s*(m|M|min|mins|minute|minutes))?\s*(?:(?P<seconds>\d+)\s*(s|S|sec|secs|second|seconds))?\s*$")
SIMPLE_TIME_RE = re.compile(r"^(?P<hours>\d+)$")
TUPLE_RE = re.compile(r"^\d+,\d+\Z")
MENTION_RE = re.compile(r"^<@!(\d)+>$")


def get_human_time(elapsed_time):
    _elapsed_seconds = elapsed_time.seconds + elapsed_time.days * 24 * 3600
    
    _days = _elapsed_seconds // (24 * 3600)
    _elapsed_seconds %= 24 * 3600
    
    _hours = _elapsed_seconds // 3600
    _elapsed_seconds %= 3600

    _minutes = _elapsed_seconds // 60
    _elapsed_seconds %= 60

    _seconds = _elapsed_seconds

    _human_time = io.StringIO()
    if _days:
        _human_time.write(f"{_days}d")
    if _hours:
        if _days:
            _human_time.write(f" ")
        _human_time.write(f"{_hours}h")
    if _minutes:
        if _days or _hours:
            _human_time.write(f" ")
        _human_time.write(f"{_minutes}m")
    if _seconds:
        if _days or _hours or _minutes:
            _human_time.write(f" ")
        _human_time.write(f"{_seconds}s")

    return _human_time.getvalue()


def parse_time(input_time):
    _total_seconds = None
    if input_time:
        _m = COMPLEX_TIME_RE.match(input_time)
        if _m:
            _matches = _m.groupdict(0)
            _days, _hours, _minutes, _seconds = map(int, (_matches.get('days', 0), _matches.get('hours', 0), _matches.get('minutes', 0), _matches.get('seconds', 0)))
            _total_seconds = _days * 86400 + _hours * 3600 + _minutes * 60 + _seconds
        else:
            _m = SIMPLE_TIME_RE.match(input_time)
            if _m:
                _matches = _m.groupdict(0)
                _total_seconds = int(_matches.get('hours', 0)) * 3600
    return _total_seconds


def is_tuple(string):
    if TUPLE_RE.match(string):
        return True
    else:
        return False


def is_mention(string):
    if MENTION_RE.match(string):
        return True
    else:
        return False


def get_member_name(mention_string, mentions):
    _m = MENTION_RE.match(mention_string)
    if not _m or not mentions:
        return mention_string
    elif len(mentions) == 1:
        return mentions[0].name
    else:
        _user_id = _m.groups()[0]
        for _mention in mentions:
            if _mention.id == _user_id:
                return _mention.id

        return mention_string
