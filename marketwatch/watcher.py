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
from . import stats
from . import utils
from . import worker

class Watcher():
    """
    Continually updates ESI market data
    """
    class _UpdateGroupInfoTask():
        def __init__(self, global_api, group_ids):
            self.__global_api = global_api
            self.__group_ids = group_ids

        def __call__(self, pool, worker):
            group_infos = []
            for group_id in self.__group_ids:
                group_infos.append(
                    self.__global_api.fetch_market_group_info(worker, group_id))
            worker.database().add_market_group_info(worker, group_infos)

    class _UpdateGroupsTask():
        def __init__(self, global_api):
            self.__global_api = global_api

        def __call__(self, pool, worker):
            group_ids = self.__global_api.fetch_market_groups(worker)
            worker.database().add_market_groups(worker, group_ids)

            for sub_list in utils.list_chunks(group_ids, 8):
                pool.enqueue(
                    Watcher._UpdateGroupInfoTask(self.__global_api, sub_list))

    class _UpdateOrdersTask():
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
        self.__fetch_delay = config['fetch_delay']
        self.__global_api = api.API(config, 0)
        self.__wait_delay = config['wait_delay']
        self.__worker_pool = worker.WorkerPool(config)

        self.__region_apis = {}
        for region_id in config['regions']:
            self.__region_apis[region_id] = api.API(config, region_id)

    def watch(self):
        """
        Enters a blocking loop that fetches data, updates the database and
        sleeps for the remaning time as defined in the config
        """
        schedule.every().day.at("11:30").do(
            self.__update_groups).run()
        return
        schedule.every(self.__fetch_delay).seconds.do(
            self.__update_orders).run()

        while True:
            schedule.run_pending()
            self.__worker_pool.wait()
            time.sleep(self.__wait_delay)

    def __update_groups(self):
        self.__worker_pool.log().info("Updating market groups")
        self.__worker_pool.enqueue(Watcher._UpdateGroupsTask(self.__global_api))

    def __update_orders(self):
        self.__worker_pool.log().info("Updating orders for all regions")
        for _, region_api in self.__region_apis.items():
            self.__worker_pool.enqueue(Watcher._UpdateOrdersTask(region_api))
