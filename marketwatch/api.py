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
Defines an API endpoint for fetching orders and static data from ESI.
"""

import threading
import time

from . import stats

class API():
    """
    Contains metadata about an update operation for a specific region, and
    methods for making ESI API calls. Methods are thread safe.
    """

    # The API endpoint for requesting region information for a given ID
    __REGION_INFO   = 'https://esi.evetech.net/latest/universe/regions/{}'

    # The API endpoint for requesting constellation information for a given ID
    __CONST_INFO    = 'https://esi.evetech.net/latest/universe/constellations/{}'

    # The API endpoint for requesting system information for a given ID
    __SYSTEM_INFO   = 'https://esi.evetech.net/latest/universe/systems/{}'


    # The API endpoint for requesting market group IDs and market group
    # info
    __MARKET_GROUPS = 'https://esi.evetech.net/latest/markets/groups/{}'

    # The API endpoint for requesting orders in a region, optionally with
    # a specified item type ID filter
    __REGION_ORDERS = 'https://esi.evetech.net/latest/markets/{}/orders/'

    # The API endpoint for requesting the item type IDs wih active orders
    # in the specified region
    __REGION_TYPES  = 'https://esi.evetech.net/latest/markets/{}/types/'


    class Page():
        """
        Utility for tracking a paged resource from ESI. Tracks a page number
        and caching etag
        """

        def __init__(self, number):
            self.etag = ""
            self.number = number
            self.cache = None

    def __init__(self, config, region_id):
        """
        Constructs a new API instance from the specified region id.

        Args:
            config: Configuration options for this API instance.
            region_id: The ID of the region that should be used for API calls.
        """

        self.__order_page_lock = threading.Lock()
        self.__order_pages = {}

        self.__type_page_lock = threading.Lock()
        self.__type_pages = {}

        self.__region_id = region_id
        self.__user_agent = config['agent']

    def region_id(self):
        """
        Returns the region ID for this API instance
        """

        return self.__region_id

    def fetch_regions(self, worker):
        """
        Fetches the list of regions IDs.

        Args:
            worker: The marketwatch.worker.Worker containing local state.

        Returns:
            The list of valid region IDs.
        """

        return self.__fetch_unpaged(
            worker, '', self.__REGION_INFO.format(''))

    def fetch_region_info(self, worker, region_id):
        """
        Fetches the info for a particular region.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The region ID to fetch.

        Returns:
            Region info fields for the specified ID.
        """

        return self.__fetch_unpaged(
            worker, '', self.__REGION_INFO.format(region_id))

    def fetch_constellation_info(self, worker, constellation_id):
        """
        Fetches the info for a particular constellaton

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            constellation_id: The constellation ID to fetch.

        Returns:
            Constellation info fields for the specified ID.
        """

        return self.__fetch_unpaged(
            worker, '', self.__CONST_INFO.format(constellation_id))

    def fetch_system_info(self, worker, system_id):
        """
        Fetches the info for a particular system

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            system_id: The system ID to fetch.

        Returns:
            System info fields for the specified ID.
        """

        return self.__fetch_unpaged(
            worker, '', self.__SYSTEM_INFO.format(system_id))

    def fetch_market_groups(self, worker):
        """
        Fetches the list of market group IDs.

        Args:
            worker: The marketwatch.worker.Worker containing local state.

        Returns:
            The list of valid market group IDs.
        """

        return self.__fetch_unpaged(
            worker, '', self.__MARKET_GROUPS.format(''))

    def fetch_market_group_info(self, worker, group_id):
        """
        Fetches the info for a particular market order.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            group_id: The market group ID to fetch.

        Returns:
            Market group info fields for the specified ID.
        """

        return self.__fetch_unpaged(
            worker, '', self.__MARKET_GROUPS.format(group_id))

    def fetch_type_orders(self, worker, type_id=None, callback=None):
        """
        Fetches orders for the specified item type ID

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            type_id: The optional item type ID to use as a filter
            callback: An optional callable to invoke for each order page.

        Returns:
            If not callback was specified, returns the list of market order
            pages, and the list of order IDs that were still cached.
        """

        return self.__fetch_paged(
            worker, callback, API.__fetch_type_order_page, type_id)

    def fetch_types(self, worker):
        """
        Fetches the list of type IDs for the region

        Args:
            worker: The marketwatch.worker.Worker containing local state.

        Returns:
            The list of item type IDs available on the market in the
            region associated with this API instance.
        """

        return self.__fetch_paged(worker, None, API.__fetch_type_page)

    def __fetch_paged(self, worker, callback, func, *args, **kwargs):
        current_page = 1
        num_errors = 3

        data_pages = []
        cache_pages = []
        with stats.Stats.Timer() as timer:
            while True:
                max_pages, data, cache = func(
                    self, worker, current_page, *args, **kwargs)

                if max_pages < 1:
                    if num_errors == 0:
                        break

                    num_errors -= 1
                    time.sleep(0.5)
                    continue

                if callback:
                    callback(data, cache)
                else:
                    if data:
                        data_pages.append(data)
                    if cache:
                        cache_pages.append(cache)

                if current_page >= max_pages:
                    break
                current_page += 1

        worker.stats().update(stats.Stats.REQUEST, runtime=timer.elapsed())
        return (data_pages, cache_pages)

    def __fetch_unpaged(self, worker, etag, req_url, **kwargs):
        num_errors = 3

        data = None
        with stats.Stats.Timer() as timer:
            while True:
                success, data = self.__fetch_api_unpaged(
                    worker, etag, req_url, **kwargs)

                if success or num_errors == 0:
                    break

                num_errors -= 1
                time.sleep(0.5)

        worker.stats().update(stats.Stats.REQUEST, runtime=timer.elapsed())
        return data

    def __fetch_type_page(self, worker, number):
        with self.__type_page_lock:
            if number in self.__type_pages:
                type_page = self.__type_pages[number]
            else:
                type_page = self.Page(number)
                self.__type_pages[number] = type_page

        req_url = self.__REGION_TYPES.format(self.__region_id)
        max_pages, orders = self.__fetch_api_page(worker, type_page, req_url)
        return (max_pages, orders, None)

    def __fetch_type_order_page(self, worker, number, type_id):
        with self.__order_page_lock:
            if not type_id in self.__order_pages:
                order_pages = self.__order_pages[type_id] = []
            else:
                order_pages = self.__order_pages[type_id]

            if number > len(order_pages):
                order_page = self.Page(number)
                order_pages.insert(number-1, order_page)
            else:
                order_page = order_pages[number-1]

        req_url = self.__REGION_ORDERS.format(self.__region_id)
        max_pages, orders = self.__fetch_api_page(
            worker, order_page, req_url, type_id=type_id)

        if orders:
            order_page.cache = []
            for order in orders:
                order_page.cache.append(int(order['order_id']))
            return (max_pages, orders, None)

        return (max_pages, orders, order_page.cache)

    def __fetch_api_page(self, worker, page, req_url, **kwargs):
        req_params = {'page': page.number}
        req_params.update(kwargs)

        request, etag = self.__fetch_api(worker, req_url, req_params, page.etag)
        page.etag = etag

        if not request:
            worker.stats().update(stats.Stats.REQUEST, total=1, failure=1)
            return (-1, None)

        if 'x-pages' in request.headers:
            max_pages = int(request.headers['x-pages'])
        else:
            max_pages = 1

        if request.status_code == 304:
            worker.stats().update(stats.Stats.REQUEST, total=1)
            return (max_pages, None)

        worker.stats().update(stats.Stats.REQUEST, total=1, changed=1)
        return (max_pages, request.json())

    def __fetch_api_unpaged(self, worker, etag, req_url, **kwargs):
        request, etag = self.__fetch_api(worker, req_url, kwargs, etag)

        if not request:
            worker.stats().update(stats.Stats.REQUEST, total=1, failure=1)
            return (False, None)

        if request.status_code == 304:
            worker.stats().update(stats.Stats.REQUEST, total=1)
            return (True, None)

        worker.stats().update(stats.Stats.REQUEST, total=1, changed=1)
        return (True, request.json())

    def __fetch_api(self, worker, url, params, etag):
        headers = {
            'If-None-Match': etag,
            'User-Agent': self.__user_agent
        }
        request = worker.session().get(url, params=params, headers=headers)

        try:
            request.raise_for_status()
        except Exception:
            worker.log().exception("API request error")
            return (None, "")

        if 'etag' in request.headers:
            etag = request.headers['etag']
        else:
            etag = ""

        return (request, etag)
