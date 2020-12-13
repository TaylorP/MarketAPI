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

import time
import schedule

from . import api
from . import database
from . import stats
from . import tasks
from . import worker

class Watcher():
    """
    Continually updates ESI market data
    """

    # UTC time to do daily updates to static data, like market order groups
    __STATIC_UPDATE_TIME = "11:30"

    def __init__(self, config):
        """
        Constructs a new market watcher instance from a config
        """

        self.__config = config
        self.__database = database.Database.instance(config)
        self.__fetch_delay = config['fetch_delay']
        self.__global_api = api.API(config, 0)
        self.__region_apis = {}
        self.__wait_delay = config['wait_delay']
        self.__worker_pool = worker.WorkerPool(config)

    def watch(self):
        """
        Enters a blocking loop that fetches data, updates the database and
        sleeps for the remaning time as defined in the config
        """

        self.__worker_pool.log().info("Scheduling initial update jobs")

        schedule.every().day.at(self.__STATIC_UPDATE_TIME).do(
            self.__update_universe).run()
        schedule.every().day.at(self.__STATIC_UPDATE_TIME).do(
            self.__update_groups).run()
        schedule.every(self.__fetch_delay).seconds.do(
            self.__update_orders).run()

        self.__worker_pool.log().info("Starting watcher loop")

        while True:
            with stats.Stats.Timer() as timer:
                schedule.run_pending()
                self.__worker_pool.wait()

            if timer.elapsed() > 1.0:
                self.__worker_pool.log().info(
                    "Processed updated in %f seconds", timer.elapsed())

            time.sleep(self.__wait_delay)

    def __update_universe(self):
        self.__worker_pool.log().info("Updating universe")
        self.__worker_pool.enqueue(tasks.UpdateRegionsTask(self.__global_api))
        self.__worker_pool.wait()

        self.__region_apis = {}
        for region_id in self.__database.get_regions():
            self.__worker_pool.log().info(
                "\tAdding regional API for %i", region_id)
            self.__region_apis[region_id] = api.API(self.__config, region_id)

    def __update_groups(self):
        self.__worker_pool.log().info("Updating market groups")
        self.__worker_pool.enqueue(tasks.UpdateGroupsTask(self.__global_api))

    def __update_orders(self):
        self.__worker_pool.log().info("Updating orders for all regions")
        for _, region_api in self.__region_apis.items():
            self.__worker_pool.enqueue(tasks.UpdateOrdersTask(region_api))
