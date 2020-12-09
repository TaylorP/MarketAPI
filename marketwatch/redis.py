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

import redis

from . import database
from . import stats

class RedisDatabase(database.Database):
    """
    Redis database implementation that stores market data to a Redis DB.
    """
    __MARKET_GROUP_SET      = 'mg'
    __MARKET_GROUP_INFO_KEY = 'mgi:{}'
    __MARKET_GROUP_TYPE_KEY = 'mgt:{}'

    __REGION_TYPE_SET       = 'rt:{}:{}'

    __MARKET_GROUP_FIELDS = [
        ('description'      , str),
        ('name'             , str),
        ('market_group_id'  , int),
        ('parent_group_id'  , int),
    ]

    def __init__(self, config):
        database.Database.__init__(self)

        self.__connection = redis.Redis(
            host = config['host'],
            port = config['port'],
            db = config['database'])

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
    def __format_fields(cls, field_spec, field_dict):
        fields = {}
        for field_key, field_type in field_spec:
            if not field_key in field_dict:
                fields[field_key] = field_type()
            else:
                fields[field_key] = field_type(field_dict[field_key])
        return fields

    def add_market_groups(self, worker, group_ids):
        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for group_id in group_ids:
                    conn.sadd(self.__MARKET_GROUP_SET, group_id)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(group_ids),
            changed=len(group_ids),
            runtime=timer.elapsed())

    def add_market_group_info(self, worker, group_infos):
        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for group_info in group_infos:
                    group_id = group_info['market_group_id']
                    conn.hset(
                        self.__group_info_name(group_id),
                        mapping=self.__format_fields(
                            self.__MARKET_GROUP_FIELDS,
                            group_info))

                    if len(group_info['types']):
                        group_types = self.__group_type_name(group_id)
                        conn.delete(group_types)
                        conn.lpush(group_types, *group_info['types'])

                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(group_infos),
            changed=len(group_info),
            runtime=timer.elapsed())

    def add_orders(self, worker, region_id, orders):
        with stats.Stats.Timer() as timer:
            with self.__connection.pipeline() as conn:
                for order in orders:
                    order_id = order['order_id']

                    conn.hset(order_id, mapping=order)
                    conn.expire(order_id, 1200)
                    conn.sadd(
                        self.__type_set_name(region_id, order['type_id']),
                        order_id)
                conn.execute()

        worker.stats().update(
            stats.Stats.UPDATE,
            total=len(orders)*3,
            changed=len(orders)*3,
            runtime=timer.elapsed())

    def get_orders(self, region_id, type_id):
        set_name = self.__type_set_name(region_id, type_id)
        order_ids = self.__connection.smembers(set_name)

        orders = []
        for order_id in order_ids:
            order_fields = self.__connection.hgetall(order_id)
            if not order_fields:
                self.__connection.srem(set_name, order_id)
            else:
                orders.append(order_fields)
        return orders

    def get_groups(self):
        group_ids = self.__connection.smembers(self.__MARKET_GROUP_SET)
        return [int(group_id) for group_id in group_ids]

    def get_group_info(self, group_id):
        group_info = self.__connection.hgetall(self.__group_info_name(group_id))
        group_info['types'] = self.__connection.lrange(
            self.__group_type_name(group_id), 0, -1)
        return group_info
