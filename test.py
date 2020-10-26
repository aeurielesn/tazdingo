import re
import unittest


from utils import *


class TestTimeRegex(unittest.TestCase):

    def _create_dict(self, days=None, hours=None, minutes=None, seconds=None):
        return {'days': days, 'hours': hours, 'minutes': minutes, 'seconds': seconds}

    def test_days(self):
        input_days = ["1d", "2D", "10day", "11days", "1 d", "2 D", "10 day", "11 days"]
        expected_days = ["1", "2", "10", "11", "1", "2", "10", "11"]
        for input_day, expected_day in zip(input_days, expected_days):
            m = COMPLEX_TIME_RE.match(input_day)
            self.assertIsNotNone(m)
            self.assertEqual(m.groupdict(), self._create_dict(days=expected_day))

    def test_hours(self):
        input_hours = ["1h", "2H", "10hour", "11hours", "1 h", "2 H", "10 hour", "11 hours"]
        expected_hours = ["1", "2", "10", "11", "1", "2", "10", "11"]
        for input_hour, expected_hour in zip(input_hours, expected_hours):
            m = COMPLEX_TIME_RE.match(input_hour)
            self.assertIsNotNone(m)
            self.assertEqual(m.groupdict(), self._create_dict(hours=expected_hour))

    def test_minutes(self):
        input_minutes = ["1m", "2M", "10mins", "11minutes", "1 m", "2 M", "10 mins", "11 minutes"]
        expected_minutes = ["1", "2", "10", "11", "1", "2", "10", "11"]
        for input_minute, expected_minute in zip(input_minutes, expected_minutes):
            m = COMPLEX_TIME_RE.match(input_minute)
            self.assertIsNotNone(m)
            self.assertEqual(m.groupdict(), self._create_dict(minutes=expected_minute))

    def test_seconds(self):
        input_seconds = ["1s", "2S", "10secs", "11seconds", "1 s", "2 S", "10 secs", "11 seconds"]
        expected_seconds = ["1", "2", "10", "11", "1", "2", "10", "11"]
        for input_second, expected_second in zip(input_seconds, expected_seconds):
            m = COMPLEX_TIME_RE.match(input_second)
            self.assertIsNotNone(m)
            self.assertEqual(m.groupdict(), self._create_dict(seconds=expected_second))


class TestParseTime(unittest.TestCase):

    def test_days(self):
        input_days = ["1d", "2D", "10day", "11days", "1 d", "2 D", "10 day", "11 days"]
        expected_seconds = [86400, 172800, 864000, 950400, 86400, 172800, 864000, 950400]
        for input_day, expected_second in zip(input_days, expected_seconds):
            actual_second = parse_time(input_day)
            self.assertIsNotNone(actual_second)
            self.assertEqual(actual_second, expected_second)

    def test_hours(self):
        input_hours = ["1h", "2H", "10hour", "11hours", "1 h", "2 H", "10 hour", "11 hours"]
        expected_seconds = [3600, 7200, 36000, 39600, 3600, 7200, 36000, 39600]
        for input_hour, expected_second in zip(input_hours, expected_seconds):
            actual_second = parse_time(input_hour)
            self.assertIsNotNone(actual_second)
            self.assertEqual(actual_second, expected_second)

    def test_minutes(self):
        input_minutes = ["1m", "2M", "10mins", "11minutes", "1 m", "2 M", "10 mins", "11 minutes"]
        expected_seconds = [60, 120, 600, 660, 60, 120, 600, 660,]
        for input_minute, expected_second in zip(input_minutes, expected_seconds):
            actual_second = parse_time(input_minute)
            self.assertIsNotNone(actual_second)
            self.assertEqual(actual_second, expected_second)

    def test_seconds(self):
        input_seconds = ["1s", "2S", "10secs", "11seconds", "1 s", "2 S", "10 secs", "11 seconds"]
        expected_seconds = [1, 2, 10, 11, 1, 2, 10, 11]
        for input_second, expected_second in zip(input_seconds, expected_seconds):
            actual_second = parse_time(input_second)
            self.assertIsNotNone(actual_second)
            self.assertEqual(actual_second, expected_second)

    def test_complex(self):
        input_seconds = ["1d 1h", "1h 1s"]
        expected_seconds = [90000, 3601]
        for input_second, expected_second in zip(input_seconds, expected_seconds):
            actual_second = parse_time(input_second)
            self.assertIsNotNone(actual_second)
            self.assertEqual(actual_second, expected_second)

    def test_simple(self):
        input_seconds = ["1", "2", "10", "11"]
        expected_seconds = [3600, 7200, 36000, 39600]
        for input_second, expected_second in zip(input_seconds, expected_seconds):
            actual_second = parse_time(input_second)
            self.assertIsNotNone(actual_second)
            self.assertEqual(actual_second, expected_second)

    def test_wrong(self):
        input_seconds = ["", "asd", "1d 1", "1x", "1s 1h"]
        for input_second in input_seconds:
            actual_second = parse_time(input_second)
            self.assertIsNone(actual_second)


if __name__ == '__main__':
    unittest.main()
