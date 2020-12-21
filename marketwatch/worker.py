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

"""Threaded pool of workers that can process tasks"""

import queue
import threading

import requests

from . import database
from . import logging
from . import stats

class Worker():
    """
    Worker
    """
    def __init__(self, config, name, index):
        self.__config = config
        self.__database = database.Database.instance(config)
        self.__index = index
        self.__log = logging.Logging.create(config, name, name.lower())
        self.__name = name
        self.__session = requests.Session()
        self.__stats = stats.Stats()

        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.__session.mount('https://', adapter)

    def database(self):
        """
        Returns the database connection associated with the worker
        """
        return self.__database

    def index(self):
        """
        Returns the worker index in the containing pool
        """
        return self.__index

    def log(self):
        """
        Returns the log writer for the worker
        """
        return self.__log

    def session(self):
        """
        Returns the HTTPS request session cache for the worker
        """
        return self.__session

    def stats(self):
        """
        Returns the stat tracking object for the worker
        """
        return self.__stats

class WorkerPool():
    """
    Pool
    """
    def __init__(self, config, base_index=0):
        self.__log = logging.Logging.create(config, "Main", "main")
        self.__queue = queue.Queue()
        self.__workers = []

        for i in range(config.getint('pool', 'size')):
            worker_index = i + base_index
            worker_name = "Worker{:02}".format(worker_index)

            worker = Worker(config, worker_name, worker_index)
            thread = threading.Thread(
                target = WorkerPool.__process,
                args = (self, worker),
                daemon = False)
            thread.start()

            self.__workers.append(worker)

    def enqueue(self, work):
        """
        Adds the specified task to the pool. The only requirement is that
        the task is a callable object
        """
        self.__queue.put(work)

    def log(self):
        """
        Returns the pool-level log instance
        """
        return self.__log

    def wait(self):
        """
        Waits for pending work to complete
        """
        self.__queue.join()

        total = stats.Stats()
        for worker in self.__workers:
            worker_stats = worker.stats()
            total += worker_stats
            worker_stats.reset()

        total.dump(self.__log)

    @staticmethod
    def __process(pool, worker):
        while True:
            work = pool.__queue.get()

            try:
                work(pool, worker)
            except Exception:
                worker.log().exception("Worker tasks error")

            pool.__queue.task_done()
