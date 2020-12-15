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
Task functors for updating data using the ESI API and storing it to a
database
"""
from . import utils

class UpdateSystemInfoTask():
    """
    Updates info for a specific block of system IDs.
    """

    def __init__(self, global_api, system_ids):
        """
        Constructs a task that updates systme info for a list of system IDs.

        Args:
            global_api: The global marketwatch.api.API instance.
            system_ids: The list of system IDs.
        """

        self.__global_api = global_api
        self.__system_ids = system_ids

    def __call__(self, pool, worker):
        worker.log().info("Fetching system info")

        system_infos = []
        for system_id in self.__system_ids:
            worker.log().info("\tFetching system %d", system_id)
            system_infos.append(
                self.__global_api.fetch_system_info(worker, system_id))

        worker.database().add_system_info(worker, system_infos)

class UpdateRegionSystemsTask():
    """
    Updates the list of systems from for a block of constellation IDs.
    """

    def __init__(self, global_api, region_id, constellation_ids):
        """
        Constructs a task that updates the system list for a list of
        constellation IDs.

        Args:
            global_api: The global marketwatch.api.API instance.
            region_id: The ID of the region that contains the constellations.
            constellation_ids: The list of constellation IDs.
        """

        self.__constellation_ids = constellation_ids
        self.__global_api = global_api
        self.__region_id = region_id

    def __call__(self, pool, worker):
        worker.log().info("Fetching systems for region %d", self.__region_id)

        system_ids = []
        for constellation_id in self.__constellation_ids:
            constellation_info = self.__global_api.fetch_constellation_info(
                worker, constellation_id)
            if 'systems' in constellation_info:
                system_ids += constellation_info['systems']

        pool.enqueue(UpdateSystemInfoTask(
            self.__global_api, system_ids))

        worker.database().set_region_systems(
            worker, self.__region_id, system_ids)

class UpdateRegionInfoTask():
    """
    Updates info for a specific block of region IDs.
    """

    def __init__(self, global_api, region_ids):
        """
        Constructs a task that updates region info for a list of region IDs.

        Args:
            global_api: The global marketwatch.api.API instance.
            region_ids: The list of region IDs.
        """

        self.__global_api = global_api
        self.__region_ids = region_ids

    def __call__(self, pool, worker):
        worker.log().info("Fetching region info")

        region_infos = []
        for region_id in self.__region_ids:
            worker.log().info("\tFetching region %d", region_id)
            region_info = self.__global_api.fetch_region_info(worker, region_id)
            if 'constellations' in region_info:
                pool.enqueue(UpdateRegionSystemsTask(
                    self.__global_api,
                    region_id,
                    region_info['constellations']))
            region_infos.append(region_info)

        worker.database().add_region_info(worker, region_infos)

class UpdateRegionsTask():
    """
    Updates the list of region IDs.
    """

    def __init__(self, global_api):
        """
        Constructs a task that updates the list of regions.

        Args:
            global_api: The global marketwatch.api.API instance.
        """
        self.__global_api = global_api

    def __call__(self, pool, worker):
        worker.log().info("Fetching region list")

        region_ids = self.__global_api.fetch_regions(worker)
        worker.database().set_regions(worker, region_ids)

        for sub_list in utils.list_chunks(region_ids, 8):
            pool.enqueue(UpdateRegionInfoTask(self.__global_api, sub_list))

class UpdateGroupInfoTask():
    """
    Updates market group info for the specified list of IDs.
    """

    def __init__(self, global_api, group_ids):
        """
        Constructs a task that updates market group info given a list of IDs.

        Args:
            global_api: The global marketwatch.api.API instance.
            group_ids: The list of IDs to fetch market group info.
        """

        self.__global_api = global_api
        self.__group_ids = group_ids

    def __call__(self, pool, worker):
        worker.log().info("Fetching market group info")

        group_infos = []
        for group_id in self.__group_ids:
            group_infos.append(
                self.__global_api.fetch_market_group_info(worker, group_id))

        worker.database().add_market_group_info(worker, group_infos)

class UpdateGroupsTask():
    """
    Updates the list of market group IDs.
    """

    def __init__(self, global_api):
        """
        Constucts a task that updates the list of market groups.

        Args:
            global_api: The global marketwatch.api.API instance.
        """

        self.__global_api = global_api

    def __call__(self, pool, worker):
        worker.log().info("Fetching market groups")

        group_ids = self.__global_api.fetch_market_groups(worker)
        worker.database().set_market_groups(worker, group_ids)

        for sub_list in utils.list_chunks(group_ids, 8):
            pool.enqueue(UpdateGroupInfoTask(self.__global_api, sub_list))

class UpdateOrdersTask():
    """
    Updates the list of market orders for a specific region, with an
    optional item type ID filter.
    """

    def __init__(self, region_api, type_id=None):
        """
        Constructs a task that updates all orders in the specified region,
        with the optional type ID filter.

        Args:
            region_api: The marketwatch.api.API instance for the region
            type_id: The optional item type ID filter.
        """

        self.__region_api = region_api
        self.__type_id = type_id

    def __call__(self, pool, worker):
        location_infos = []
        location_ids = []
        def __update(order_page, order_cache):
            if order_page:
                worker.log().info("\tAdding new orders")

                for order in order_page:
                    location_info = self.__region_api.fetch_location_info(
                        worker, order['location_id'])
                    if location_info:
                        location_infos.append(location_info)
                        location_ids.append(order['location_id'])

                worker.database().add_orders(
                    worker, self.__region_api.region_id(), order_page)

            if order_cache:
                worker.log().info("\tRefreshing cached orders")
                worker.database().refresh_orders(worker, order_cache)

        if self.__type_id:
            worker.log().info(
                "Fetching market orders for region `%d`, type `%d`",
                self.__region_api.region_id(),
                self.__type_id)
        else:
            worker.log().info(
                "Fetching market orders for region `%d`",
                self.__region_api.region_id())

        self.__region_api.fetch_type_orders(worker, self.__type_id, __update)

        if location_ids:
            worker.log().info("Adding %d new locations", len(location_ids))

            worker.database().add_location_info(worker, location_infos)
            worker.database().add_region_locations(
                worker, self.__region_api.region_id(), location_ids)
