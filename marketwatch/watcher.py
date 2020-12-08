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
Core watcher classes for continually fetching and storing data from the ESI
market endpoints.
"""

import gc
import time

from . import api
from . import stats
from . import worker

class Watcher():
    """
    Continually updates ESI market data
    """

    class _FetchUpdateTask():
        def __init__(self, region_api, type_id=None):
            self.__region_api = region_api
            self.__type_id = type_id

        def __call__(self, pool, worker):
            order_pages = self.__region_api.fetch_type_orders(
                worker, self.__type_id)
            for order_page in order_pages:
                worker.database().add_orders(
                    worker, self.__region_api.region_id(), order_page)

    def __init__(self, config):
        self.__config = config
        self.__worker_pool = worker.WorkerPool(config)

        self.__region_apis = {}
        for region_id in config['regions']:
            self.__region_apis[region_id] = api.API(region_id)

    def watch(self):
        """
        Enters a blocking loop that fetches data, updates the database and
        sleeps for the remaning time as defined in the config
        """
        while True:
            self.__worker_pool.log().info("Updating orders for all regions")

            with stats.Stats.Timer() as timer:
                for _, region_api in self.__region_apis.items():
                    self.__worker_pool.enqueue(
                        Watcher._FetchUpdateTask(region_api))
                self.__worker_pool.wait()

            gc.collect()

            wait_time = max(0, self.__config['min_time'] - timer.elapsed())
            msg = "Updated in {:.2f} seconds, waiting for {:.2f} seconds".format(
                timer.elapsed(), wait_time)
            self.__worker_pool.log().info(msg)

            time.sleep(wait_time)
