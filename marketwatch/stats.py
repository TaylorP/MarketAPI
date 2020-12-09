#
# Copyright 2020 Taylor Petrick
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

"""
Utilies for tracking request and update stats
"""

import time

class Stats():
    """
    Utility object for tracking various API and DB statistic while updating
    market state
    """
    REQUEST, UPDATE, NUM_STATS = range(3)
    __NAMES = ["Request", "Database"]

    class StatError(Exception):
        """
        Thrown when an invalid stat value is passed to a stat query
        function
        """

    class Timer():
        """
        Records the elapsed time while the object is active, used in a
        `with` statement.
        """

        def __init__(self):
            """
            Constructs a new, empty Timer object
            """
            self.__start = 0
            self.__end = 0

        def elapsed(self):
            """
            Returns the elapsed time. This value is cached on the timer and
            is valid even after the context manager block exits
            """
            return self.__end - self.__start

        def __enter__(self):
            self.__start = time.time()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.__end = time.time()

    def __init__(self):
        """
        Constructs a zero initialized stat tracker
        """
        self.__total = [0] * self.NUM_STATS
        self.__changed = [0] * self.NUM_STATS
        self.__failure = [0] * self.NUM_STATS
        self.__time = [0] * self.NUM_STATS

    def dump(self, log):
        """
        Dumps the current stats to the specified log
        """

        for i in range(self.NUM_STATS):
            name = self.__NAMES[i]
            if not self.total(i):
                continue
            log.info("\t[%s] totals:\t%d", name, self.total(i))
            log.info("\t[%s] changed:\t%d", name, self.changed(i))
            log.info("\t[%s] failures:\t%d", name, self.failure(i))
            log.info("\t[%s] time (s):\t%f", name, self.time(i))
            log.info("\t[%s] avg (s):\t%f", name, self.avg_time(i))

    def update(self, stat, total=0, changed=0, failure=0, runtime=0):
        """
        Updates any number of fields for the specified stat time
        """
        try:
            self.__total[stat] += total
            self.__changed[stat] += changed
            self.__failure[stat] += failure
            self.__time[stat] += runtime
        except (IndexError, TypeError):
            raise self.StatError("invalid stat type {}".format(stat))

    def reset(self):
        """
        Resets all stat counters back to 0.
        """
        self.__total = [0] * self.NUM_STATS
        self.__changed = [0] * self.NUM_STATS
        self.__failure = [0] * self.NUM_STATS
        self.__time = [0] * self.NUM_STATS

    def total(self, stat):
        """
        Returns the total event count for the specified stat query
        """
        try:
            return self.__total[stat]
        except (IndexError, TypeError):
            raise self.StatError("invalid stat type {}".format(stat))

    def changed(self, stat):
        """
        Returns the change/uncached  event count for the specified stat query
        """
        try:
            return self.__changed[stat]
        except (IndexError, TypeError):
            raise self.StatError("invalid stat type {}".format(stat))

    def failure(self, stat):
        """
        Returns the failure event count for the specified stat query
        """
        try:
            return self.__failure[stat]
        except (IndexError, TypeError):
            raise self.StatError("invalid stat type {}".format(stat))

    def time(self, stat):
        """
        Returns the total time accross all of the specified events
        """
        try:
            return self.__time[stat]
        except (IndexError, TypeError):
            raise self.StatError("invalid stat type {}".format(stat))

    def avg_time(self, stat):
        """
        Returns the average time accross of the specified events
        """
        try:
            if self.__total[stat] == 0:
                return 0
            return self.__time[stat]/self.__total[stat]
        except (IndexError, TypeError):
            raise self.StatError("invalid stat type {}".format(stat))

    def __iadd__(self, other):
        """
        Adds another stat object onto this one
        """
        if type(other) != type(self):
            raise TypeError(
                "unsupported operand type(s) for +: '{}' and '{}'".format(
                    type(other), type(self)))

        for i in range(0, self.NUM_STATS):
            self.__total[i] += other.__total[i]
            self.__changed[i] += other.__changed[i]
            self.__failure[i] += other.__failure[i]
            self.__time[i] += other.__time[i]

        return self

    def __add__(self, other):
        """
        Adds two stat objects together
        """
        if type(other) != type(self):
            raise TypeError(
                "unsupported operand type(s) for +: '{}' and '{}'".format(
                    type(other), type(self)))

        combined = Stats()
        for i in range(0, self.NUM_STATS):
            combined.__total[i] = self.__total[i] + other.__total[i]
            combined.__changed[i] = self.__changed[i] + other.__changed[i]
            combined.__failure[i] = self.__failure[i] + other.__failure[i]
            combined.__time[i] = self.__time[i] + other.__time[i]

        return combined
