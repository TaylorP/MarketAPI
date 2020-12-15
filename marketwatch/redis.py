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
Redis database interface
"""

import datetime
import redis

from . import database
from . import stats

class RedisDatabase(database.Database):
    """
    Redis database implementation that stores market data to a Redis DB.
    """

    # The key for the Redis LIST that contains all of the region IDs
    __REGION_LIST           = 'r'

    # The key format for a Redis HASH that contains the info data for the
    # matching region ID
    __REGION_INFO_KEY       = 'ri:{}'

    # The key format for a Redis LIST that contains the systems IDs in a
    # matching region ID
    __REGION_SYSTEM_KEY     = 'rs:{}'

    # The key format for a Redis LIST that contains the locaton IDs in a
    # matching region ID
    __REGION_LOCATION_KEY   = 'rl:{}'

    # The key format for a Redis HASH that contains the info data for the
    # matching system ID
    __SYSTEM_INFO_KEY       = 'si:{}'

    # The key format for a Redis HASH that contains the info data for the
    # location ID
    __LOCATION_INFO_KEY     = 'li:{}'


    # The key for the Redis LIST that contains all of the market group IDs
    __MARKET_GROUP_LIST     = 'mg'

    # The key format for a Redis HASH that contains the info data for the
    # matching market group ID
    __MARKET_GROUP_INFO_KEY = 'mgi:{}'

    # The key for the market group type LIST that contains the list of item
    # type IDs for the matchign market group ID
    __MARKET_GROUP_TYPE_KEY = 'mgt:{}'

    # The key expiry in seconds for market orders
    __MARKET_ORDER_TTL      = 1200


    # The key format for the Redis SET containing market order IDs for the
    # matching region and item type ID
    __REGION_TYPE_SET       = 'rt:{}:{}'

    # The time format used in market orders to specify the date/time that the
    # order was listed
    __TIME_FORMAT           = '%Y-%m-%dT%H:%M:%SZ'


    # Field names -> types from a region info API request that should
    # be stored
    __REGION_FIELDS = [
        ('name'             , 'name'    , str),
        ('region_id'        , 'id'      , int),
    ]

    # Field names -> types from a system info API request that should
    # be stored
    __SYSTEM_FIELDS = [
        ('name'             , 'name'    , str),
        ('security_status'  , 'sec'     , float),
        ('system_id'        , 'id'      , int),
    ]

    # Field names -> types from a structure or station API request that
    # should be stored
    __LOCATION_FIELDS = [
        ('name'             , 'name'    , str),
        ('station_id'       , 'id'      , int),
    ]

    # Field names -> types from a market group info API request that should
    # be stored
    __MARKET_GROUP_FIELDS = [
        ('name'             , 'name'    , str),
        ('market_group_id'  , 'id'      , int),
        ('parent_group_id'  , 'pid'     , int),
    ]

    # Field names -> types for a market order API request that should be
    # stored
    __ORDER_FIELDS = [
        ('system_id'        , 'sid'     , int),
        ('location_id'      , 'lid'     , int),
        ('is_buy_order'     , 'buy'     , int),
        ('min_volume'       , 'minvol'  , int),
        ('volume_total'     , 'totvol'  , int),
        ('volume_remain'    , 'remvol'  , int),
        ('price'            , 'price'   , float),
        ('range'            , 'range'   , str),
    ]

    def __init__(self, config):
        """
        Constructs a new database connection.

        Args:
            config: The configuration options for the database.
        """

        database.Database.__init__(self)

        self.__connection = redis.StrictRedis(
            host = config['host'],
            port = config['port'],
            db = config['database'],
            decode_responses=True)

    def set_regions(self, worker, region_ids):
        """
        Stores the specified region IDs to a set in the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_ids: The list of region IDs to add to the database.
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                conn.delete(self.__REGION_LIST)
                conn.rpush(self.__REGION_LIST, *region_ids)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(region_ids),
            changed=len(region_ids),
            runtime=timer.elapsed())

    def add_region_info(self, worker, region_infos):
        """
        Adds the specified region infos to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_infos: The list of region info fields to add.
        """

        self.__add_infos(
            worker,
            region_infos,
            self.__REGION_FIELDS,
            'region_id',
            self.__region_info_name)

    def set_region_systems(self, worker, region_id, system_ids):
        """
        Sets the system IDs in the the specified region.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The ID of the region that contains the systems.
            system_ids: The list of system IDs.
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                system_key = self.__region_system_name(region_id)
                conn.delete(system_key)
                conn.rpush(system_key, *system_ids)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(system_ids),
            changed=len(system_ids),
            runtime=timer.elapsed())

    def add_system_info(self, worker, system_infos):
        """
        Adds the specified region infos to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_infos: The list of region info fields to add.
        """

        self.__add_infos(
            worker,
            system_infos,
            self.__SYSTEM_FIELDS,
            'system_id',
            self.__system_info_name)

    def add_region_locations(self, worker, region_id, location_ids):
        """
        Adds the locations IDs in the specified region.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The ID of the region that contains the locations.
            locations_ids: The list of location IDs.
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                location_key = self.__region_location_name(region_id)
                conn.rpush(location_key, *location_ids)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(location_ids),
            changed=len(location_ids),
            runtime=timer.elapsed())

    def add_location_info(self, worker, location_infos):
        """
        Adds the specified location infos to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            location_infos: The list of location info fields to add.
        """

        self.__add_infos(
            worker,
            location_infos,
            self.__LOCATION_FIELDS,
            'station_id',
            self.__location_info_name)

    def set_market_groups(self, worker, group_ids):
        """
        Stores the specified market group IDs to a set in the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            group_ids: A list of market group IDs to add to the database.
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                conn.delete(self.__MARKET_GROUP_LIST)
                conn.rpush(self.__MARKET_GROUP_LIST, *group_ids)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(group_ids),
            changed=len(group_ids),
            runtime=timer.elapsed())

    def add_market_group_info(self, worker, group_infos):
        """
        Adds the specified market group infos to the database, and stores the
        types for each group into a list.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            group_infos: The list of market group info fields to add.
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for group_info in group_infos:
                    group_id = group_info['market_group_id']
                    conn.hset(
                        self.__group_info_name(group_id),
                        mapping=self.__extract_fields(
                            self.__MARKET_GROUP_FIELDS,
                            group_info))

                    type_list = group_info['types']
                    if type_list:
                        group_types = self.__group_type_name(group_id)
                        conn.delete(group_types)
                        conn.lpush(group_types, *type_list)

                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(group_infos),
            changed=len(group_infos),
            runtime=timer.elapsed())

    def add_orders(self, worker, region_id, orders):
        """
        Adds the orders to the database and the matching region::type set for
        the order.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The region ID that the order(s) are listed in.
            orders: The list of market order fields to add.
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for order in orders:
                    order_id = order['order_id']

                    conn.set(order_id, self.__encode_order(order))
                    conn.expire(order_id, self.__MARKET_ORDER_TTL)
                    conn.sadd(
                        self.__type_set_name(region_id, order['type_id']),
                        order_id)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(orders)*3,
            changed=len(orders)*3,
            runtime=timer.elapsed())

    def refresh_orders(self, worker, order_ids):
        """
        Refreshes the orders with the specified IDs. This only affects the
        TTL value for existing order keys -- this method does not add any
        new keys to the database.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            order_ids: The list of market order IDs that need a TTL refresh
        """

        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for order_id in order_ids:
                    conn.expire(order_id, self.__MARKET_ORDER_TTL)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(order_ids),
            changed=len(order_ids),
            runtime=timer.elapsed())

    def get_regions(self):
        """
        Queries the list of region IDs.

        Returns:
            The list of valud region IDs.
        """

        region_ids = self.__connection.lrange(self.__REGION_LIST, 0, -1)
        return [int(region_id) for region_id in region_ids]

    def get_region_info(self, region_id):
        """
        Queries region info for the specified ID.

        Args:
            region_id: The region ID to lookup in the database.

        Returns:
            The region info for the specified ID.
        """

        region_info = self.__cast_fields(
            self.__REGION_FIELDS,
            self.__connection.hgetall(self.__region_info_name(region_id)))
        return region_info

    def get_systems(self, region_id):
        """
        Queries the list of system IDs for the given region ID.

        Args:
            region_id:  The region ID to lookup in the database.

        Returns:
            The list of system IDs in the specified region ID.
        """

        system_ids = self.__connection.lrange(
            self.__region_system_name(region_id), 0, -1)
        return [int(system_id) for system_id in system_ids]

    def get_system_info(self, system_id):
        """
        Queries system info for the specified ID.

        Args:
            system_id: The system ID to lookup in the database.

        Returns:
            The system info for the specified ID.
        """

        system_info = self.__cast_fields(
            self.__SYSTEM_FIELDS,
            self.__connection.hgetall(self.__system_info_name(system_id)))
        return system_info

    def get_locations(self, region_id):
        """
        Queries the list of locatons IDs for the given region ID.

        Args:
            region_id:  The region ID to lookup in the database.

        Returns:
            The list of location IDs in the specified region ID.
        """

        location_ids = self.__connection.lrange(
            self.__region_location_name(region_id), 0, -1)
        return [int(location_id) for location_id in location_ids]

    def get_location_info(self, location_id):
        """
        Queries location info for the specified ID.

        Args:
            location_id: The location ID to lookup in the database.

        Returns:
            The location info for the specified ID.
        """

        location_info = self.__cast_fields(
            self.__LOCATION_FIELDS,
            self.__connection.hgetall(self.__location_info_name(location_id)))
        return location_info

    def get_groups(self):
        """
        Queries all market group IDs.

        Returns:
            The list of market group IDs in the database.
        """

        group_ids = self.__connection.lrange(self.__MARKET_GROUP_LIST, 0, -1)
        return [int(group_id) for group_id in group_ids]

    def get_group_info(self, group_id):
        """
        Queries market group info for the specified ID.

        Args:
            group_id: The market group ID to lookup in the database

        Returns:
            The market group info for the specified ID.
        """

        group_info = self.__cast_fields(
            self.__MARKET_GROUP_FIELDS,
            self.__connection.hgetall(self.__group_info_name(group_id)))
        type_ids = self.__connection.lrange(
            self.__group_type_name(group_id), 0, -1)
        group_info['types'] = [int(type_id) for type_id in type_ids]
        return group_info

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

        set_name = self.__type_set_name(region_id, type_id)
        order_ids = self.__connection.smembers(set_name)

        if orders is None:
            orders = []

        for order_id in order_ids:
            encoded_order = self.__connection.get(order_id)
            if not encoded_order:
                self.__connection.srem(set_name, order_id)
            else:
                ttl = self.__connection.ttl(order_id)
                order_fields = self.__decode_order(encoded_order)
                order_fields['age'] = (self.__MARKET_ORDER_TTL - ttl)
                orders.append(order_fields)

        return orders

    @classmethod
    def __region_info_name(cls, region_id):
        return cls.__REGION_INFO_KEY.format(region_id)

    @classmethod
    def __region_system_name(cls, region_id):
        return cls.__REGION_SYSTEM_KEY.format(region_id)

    @classmethod
    def __region_location_name(cls, region_id):
        return cls.__REGION_LOCATION_KEY.format(region_id)

    @classmethod
    def __system_info_name(cls, system_id):
        return cls.__SYSTEM_INFO_KEY.format(system_id)

    @classmethod
    def __location_info_name(cls, location_id):
        return cls.__LOCATION_INFO_KEY.format(location_id)

    @classmethod
    def __group_info_name(cls, group_id):
        return cls.__MARKET_GROUP_INFO_KEY.format(group_id)

    @classmethod
    def __group_type_name(cls, group_id):
        return cls.__MARKET_GROUP_TYPE_KEY.format(group_id)

    @classmethod
    def __type_set_name(cls, region_id, type_id):
        return cls.__REGION_TYPE_SET.format(region_id, type_id)

    @classmethod
    def __extract_fields(cls, field_spec, field_dict):
        fields = {}
        for field_key, field_name, field_type in field_spec:
            if field_key in field_dict:
                fields[field_name] = field_type(field_dict[field_key])
        return fields

    @classmethod
    def __cast_fields(cls, field_spec, field_dict):
        fields = {}
        for _, field_name, field_type in field_spec:
            if field_name in field_dict:
                fields[field_name] = field_type(field_dict[field_name])
        return fields

    @classmethod
    def __encode_fields(cls, field_dict):
        return ':'.join([str(field) for _, field in field_dict.items()])

    @classmethod
    def __decode_fields(cls, field_spec, field_string, **kwargs):
        field_components = field_string.split(':')
        decoded_fields = {}

        index = 0
        for _, field_name, field_type in field_spec:
            decoded_fields[field_name] = field_type(field_components[index])
            index += 1

        for field_name, field_type in kwargs.items():
            decoded_fields[field_name] = field_type(field_components[index])
            index += 1

        return decoded_fields

    @classmethod
    def __encode_order(cls, order_dict):
        order_fields = cls.__extract_fields(cls.__ORDER_FIELDS, order_dict)

        issued = datetime.datetime.strptime(
            order_dict['issued'], cls.__TIME_FORMAT)
        issued += datetime.timedelta(int(order_dict['duration']))
        order_fields['expiry'] = int(issued.timestamp())

        return cls.__encode_fields(order_fields)

    @classmethod
    def __decode_order(cls, order_string):
        return cls.__decode_fields(cls.__ORDER_FIELDS, order_string, expiry=int)

    def __add_infos(self, worker, infos, field_spec, id_key, hash_func):
        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for info in infos:
                    info_id = info[id_key]
                    conn.hset(
                        hash_func(info_id),
                        mapping=self.__extract_fields(field_spec, info))
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(infos),
            changed=len(infos),
            runtime=timer.elapsed())
