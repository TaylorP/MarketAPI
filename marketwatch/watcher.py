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
from . import search
from . import stats
from . import tasks
from . import worker

class Watcher():
    """
    Continually updates ESI market data
    """

    def __init__(self, config):
        """
        Constructs a new market watcher instance from a config
        """

        self.__config = config
        self.__database = database.Database.instance(config)
        self.__global_api = api.GlobalAPI(config)
        self.__region_apis = {}
        self.__worker_pool = worker.WorkerPool(config)

        self.__group_job = schedule.every().day.at(
            config.get('job', 'static_time')).do(self.__update_groups)
        self.__order_job = schedule.every(
            config.getint('job', 'update_rate')).seconds.do(self.__update_orders)
        self.__universe_job = schedule.every().day.at(
            config.get('job', 'static_time')).do(self.__update_universe)

        self.__group_cached = False
        self.__universe_cached = False

    def watch(self):
        """
        Enters a blocking loop that fetches data, updates the database and
        sleeps for the remaning time as defined in the config
        """

        self.__worker_pool.log().info("Scheduling and running initial jobs")

        self.__universe_job.run()
        self.__group_job.run()
        self.__order_job.run()

        self.__worker_pool.log().info(
            "Starting job loop w/ update rate of %ds",
            self.__config.getint('pool', 'update_rate'))
        self.__worker_pool.log().info(
            "\tFetching orders every %d seconds",
            self.__config.getint('job', 'update_rate'))
        self.__worker_pool.log().info(
            "\tStatic data update occurs daily at %s",
            self.__config.get('job', 'static_time'))

        while True:
            with stats.Stats.Timer() as timer:
                schedule.run_pending()
                self.__worker_pool.wait()

            if not self.__universe_cached:
                self.__database.set_universe_cache_expiry(
                    self.__universe_job.last_run,
                    self.__universe_job.next_run)
                self.__universe_cached = True

            if not self.__group_cached:
                self.__database.set_market_group_cache_expiry(
                    self.__group_job.last_run,
                    self.__group_job.next_run)
                self.__group_cached = True

            if timer.elapsed() > 1.0:
                self.__worker_pool.log().info(
                    "Processed updated in %f seconds", timer.elapsed())

            time.sleep(self.__config.getint('pool', 'update_rate'))


    def __refresh_access(self):
        if not self.__config.getboolean('job', 'authenticate'):
            return

        self.__worker_pool.log().info("Refreshing API access token")

        try:
            data = self.__global_api.fetch_access()

            access_token = data['access_token']
            refresh_token = data['refresh_token']

            self.__global_api.set_access(access_token, refresh_token)
            for _, region_api in self.__region_apis.items():
                region_api.set_access(access_token, refresh_token)

        except:
            self.__worker_pool.log().exception(
                "Unable to authenticate with ESI")

            self.__global_api.set_access()
            for _, region_api in self.__region_apis.items():
                region_api.set_access()

    def __init_region_apis(self):
        self.__region_apis = {}

        for region_id in self.__database.get_regions():
            self.__worker_pool.log().info(
                "\tAdding regional API for %i", region_id)
            self.__region_apis[region_id] = api.RegionalAPI(
                self.__config, region_id)

    def __update_universe(self):
        if self.__config.getboolean('job', 'regions'):
            self.__worker_pool.log().info("Updating universe")
            self.__worker_pool.enqueue(
                tasks.UpdateRegionsTask(self.__global_api))
            self.__worker_pool.wait()
        else:
            self.__worker_pool.log().info("Skipping universe update")

        self.__init_region_apis()
        self.__universe_cached = False

    def __update_groups(self):
        if self.__config.getboolean('job', 'groups'):
            self.__worker_pool.log().info("Updating market groups")
            self.__worker_pool.enqueue(tasks.UpdateGroupsTask(self.__global_api))
        else:
            self.__worker_pool.log().info("Skipping market group update")

        if self.__config.getboolean('job', 'index'):
            self.__worker_pool.wait()

            self.__worker_pool.log().info("Building search index")
            with stats.Stats.Timer() as timer:
                index = search.SearchIndex(self.__config)
                index.build_index(self.__database, True)
            self.__worker_pool.log().info("Built index in %f seconds",
                timer.elapsed())

        self.__group_cached = False

    def __update_orders(self):
        if self.__config.getboolean('job', 'orders'):
            self.__refresh_access()
            self.__worker_pool.log().info("Updating orders for all regions")
            for _, region_api in self.__region_apis.items():
                self.__worker_pool.enqueue(tasks.UpdateOrdersTask(region_api))
        else:
            self.__worker_pool.log().info("Skipping order update")
