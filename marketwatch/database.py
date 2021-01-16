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
Generic database interface for storing and retrieving market orders.
"""

class Database():
    """
    Generic database interface for storing market orders
    """

    @classmethod
    def instance(cls, config, database=None):
        """
        Returns a new database instance from the supplied config dictionary
        """
        if config.get('database', 'type') == 'redis':
            from . import redis
            db = database if database else config.getint('database', 'database')
            return redis.RedisDatabase(config, db)

        raise NotImplementedError

    def set_regions(self, worker, region_ids):
        """
        Stores the specified region IDs to a set in the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_ids: The list of region IDs to add to the database.
        """

        raise NotImplementedError

    def add_region_info(self, worker, region_infos):
        """
        Adds the specified region infos to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_infos: The list of region info fields to add.
        """

        raise NotImplementedError

    def set_region_systems(self, worker, region_id, system_ids):
        """
        Sets the system IDs in the the specified region.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The ID of the region that contains the systems.
            system_ids: The list of system IDs.
        """

        raise NotImplementedError

    def add_system_info(self, worker, system_infos):
        """
        Adds the specified region infos to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_infos: The list of region info fields to add.
        """

        raise NotImplementedError

    def add_region_locations(self, worker, region_id, location_ids):
        """
        Adds the locations IDs in the specified region.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The ID of the region that contains the locations.
            locations_ids: The list of location IDs.
        """

        raise NotImplementedError

    def add_location_info(self, worker, location_infos):
        """
        Adds the specified location infos to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            location_infos: The list of location info fields to add.
        """

        raise NotImplementedError


    def set_market_groups(self, worker, group_ids):
        """
        Stores the specified market group IDs to a set in the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            group_ids: A list of market group IDs to add to the database.
        """

        raise NotImplementedError

    def add_market_group_info(self, worker, group_infos):
        """
        Adds the specified market group infos to the database, and stores the
        types for each group into a list.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            group_infos: The list of market group info fields to add.
        """

        raise NotImplementedError

    def add_orders(self, worker, region_id, orders):
        """
        Adds the orders to the database and the matching region::type set for
        the order.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The region ID that the order(s) are listed in.
            orders: The list of market order fields to add.
        """

        raise NotImplementedError

    def refresh_orders(self, worker, order_ids):
        """
        Refreshes the orders with the specified IDs. This only affects the
        TTL value for existing order keys -- this method does not add any
        new keys to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            order_ids: The list of market order IDs that need a TTL refresh
        """

        raise NotImplementedError

    def get_regions(self):
        """
        Queries the list of region IDs.

        Returns:
            The list of valud region IDs.
        """

        raise NotImplementedError

    def get_region_info(self, region_id):
        """
        Queries region info for the specified ID.

        Args:
            region_id: The region ID to lookup in the database.

        Returns:
            The region info for the specified ID.
        """

        raise NotImplementedError

    def get_systems(self, region_id):
        """
        Queries the list of system IDs for the given region ID.

        Args:
            region_id:  The region ID to lookup in the database.

        Returns:
            The list of system IDs in the specified region ID.
        """

        raise NotImplementedError

    def get_system_info(self, system_id):
        """
        Queries system info for the specified ID.

        Args:
            system_id: The system ID to lookup in the database.

        Returns:
            The system info for the specified ID.
        """

        raise NotImplementedError

    def get_locations(self, region_id):
        """
        Queries the list of locatons IDs for the given region ID.

        Args:
            region_id:  The region ID to lookup in the database.

        Returns:
            The list of location IDs in the specified region ID.
        """

        raise NotImplementedError

    def get_location_info(self, location_id):
        """
        Queries location info for the specified ID.

        Args:
            location_id: The location ID to lookup in the database.

        Returns:
            The location info for the specified ID.
        """

        raise NotImplementedError

    def get_groups(self):
        """
        Queries all market group IDs.

        Returns:
            The list of market group IDs in the database.
        """

        raise NotImplementedError

    def get_group_info(self, group_id):
        """
        Queries market group info for the specified ID.

        Args:
            group_id: The market group ID to lookup in the database

        Returns:
            The market group info for the specified ID.
        """

        raise NotImplementedError

    def get_orders(self, region_id, type_id, orders=None):
        """
        Queries market orders for the specified region ID and type ID.

        Args:
            region_id: The region ID for filtering market orders
            type_id: The item type ID for the orders to query
            orders: Optional list in which order infos should be written
            locations: Optional set in which location IDs should be added

        Returns:
            The list of market orders for the item type in the specified
            region.
        """

        raise NotImplementedError
