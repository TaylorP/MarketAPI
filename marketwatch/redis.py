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
    __REGION_TYPE_SET = 'rt:{}:{}'

    def __init__(self, config):
        database.Database.__init__(self)

        self.__connection = redis.Redis(
            host = config['host'],
            port = config['port'],
            db = config['database'])

    @classmethod
    def __type_set_name(cls, region_id, type_id):
        return cls.__REGION_TYPE_SET.format(
            region_id, type_id)

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
            total=len(orders),
            changed=len(orders),
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
