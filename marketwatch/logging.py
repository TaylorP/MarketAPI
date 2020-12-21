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
Utilities for creating and interacting with log files
"""

import logging
import os

from logging import StreamHandler
from logging.handlers import RotatingFileHandler

class Logging():
    """
    Utilities for creating log files on disk
    """

    @classmethod
    def create(cls, config, log_name, log_file):
        """
        Creates a rolling log
        """

        os.makedirs(config.get('logging', 'dir'), exist_ok=True)

        log = logging.getLogger(log_name)
        log.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '[%(levelname)s]: %(asctime)s -- %(message)s')

        handler = RotatingFileHandler(
            '{}/{}.log'.format(config.get('logging', 'dir'), log_file),
            maxBytes = config.getint('logging', 'roll_size'),
            backupCount = config.getint('logging', 'roll_count'))
        handler.setFormatter(formatter)
        log.addHandler(handler)

        if config.getboolean('logging', 'shell'):
            error_handler = StreamHandler()
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            log.addHandler(error_handler)

        return log
