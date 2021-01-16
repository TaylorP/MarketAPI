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
Defines an API endpoints for fetching market orders and static data from ESI.
"""

import base64
import threading
import time

import requests

from . import stats

class GlobalAPI():
    """
    Base class for ESI API end points, and for fetching static data.
    """

    # The API endpoint for requesting an access token using auth info
    __AUTH          = 'https://login.eveonline.com/oauth/token'

    # The API endpoint for requesting region information for a given ID
    __REGION_INFO   = 'https://esi.evetech.net/latest/universe/regions/{}'

    # The API endpoint for requesting constellation information for a given ID
    __CONST_INFO    = 'https://esi.evetech.net/latest/universe/constellations/{}'

    # The API endpoint for requesting system information for a given ID
    __SYSTEM_INFO   = 'https://esi.evetech.net/latest/universe/systems/{}'

    # The API endpoint for requesting item type information for a given ID
    __TYPE_INFO     = 'https://esi.evetech.net/latest/universe/types/{}'

    # The API endpoint for requesting market group IDs and market group
    # info
    __MARKET_GROUPS = 'https://esi.evetech.net/latest/markets/groups/{}'

    # The number of 500 series error retries
    _ERROR_RETRIES = 3

    def __init__(self, config):
        """
        Constructs a new API instance from the config

        Args:
            config: Configuration options for this API instance.
        """

        self.__access_token = ''
        self.__app_id = config.get('request', 'appid')
        self.__app_secret = config.get('request', 'appsecret')
        self.__config = config
        self.__refresh_token = config.get('request', 'refresh_token')
        self.__user_agent = config.get('request', 'agent')

    def set_access(self, access_token='', refresh_token=''):
        """
        Updates the access and refresh token for the API instance. IF tokens
        are not provided, the access token is invalidated and the refresh
        token is reset to the one stored in the config.

        Args:
            access_token: The ESI access token for authenticated endpoints.
            refresh_token: The refresh token for requesting a new access token.
        """

        if access_token:
            self.__access_token = access_token
        else:
            self.__access_token = ''

        if refresh_token:
            self.__refresh_token = refresh_token
        else:
            self.__refresh_token = self.__config.get('request', 'refresh_token')

    def fetch_access(self):
        """
        Requests a new access token using the current refresh token

        Returns:
            The new access token.
        """

        auth_str = (self.__app_id + ':' + self.__app_secret).encode('ascii')

        headers = {
            'Authorization': 'Basic ' + base64.b64encode(auth_str).decode()
        }

        body = {
            'grant_type': 'refresh_token',
            'refresh_token': self.__refresh_token
        }

        request = requests.post(self.__AUTH, data=body, headers=headers)
        request.raise_for_status()

        return request.json()

    def fetch_regions(self, worker):
        """
        Fetches the list of regions IDs.

        Args:
            worker: The marketwatch.worker.Worker containing local state.

        Returns:
            The list of valid region IDs.
        """

        return self._fetch_unpaged(
            worker, '', self.__REGION_INFO.format(''), False)

    def fetch_region_info(self, worker, region_id):
        """
        Fetches the info for a particular region.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            region_id: The region ID to fetch.

        Returns:
            Region info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__REGION_INFO.format(region_id), False)

    def fetch_constellation_info(self, worker, constellation_id):
        """
        Fetches the info for a particular constellaton

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            constellation_id: The constellation ID to fetch.

        Returns:
            Constellation info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__CONST_INFO.format(constellation_id), False)

    def fetch_system_info(self, worker, system_id):
        """
        Fetches the info for a particular system

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            system_id: The system ID to fetch.

        Returns:
            System info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__SYSTEM_INFO.format(system_id), False)

    def fetch_type_info(self, worker, type_id):
        """
        Fetches the info for a particular item type.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            system_id: The item type ID to fetch.

        Returns:
            Type info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__TYPE_INFO.format(type_id), False)

    def fetch_market_groups(self, worker):
        """
        Fetches the list of market group IDs.

        Args:
            worker: The marketwatch.worker.Worker containing local state.

        Returns:
            The list of valid market group IDs.
        """

        return self._fetch_unpaged(
            worker, '', self.__MARKET_GROUPS.format(''), False)

    def fetch_market_group_info(self, worker, group_id):
        """
        Fetches the info for a particular market order.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            group_id: The market group ID to fetch.

        Returns:
            Market group info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__MARKET_GROUPS.format(group_id), False)

    def _fetch_unpaged(self, worker, etag, req_url, needs_auth, **kwargs):
        num_errors = 0
        data = None
        with stats.Stats.Timer() as timer:
            while True:
                success, data, status = self._fetch_api_unpaged(
                    worker, etag, req_url, needs_auth, **kwargs)

                if success or num_errors >= self._ERROR_RETRIES:
                    break

                if status < 500:
                    break

                num_errors += 1
                time.sleep(0.5*num_errors)

        worker.stats().update(stats.Stats.REQUEST, runtime=timer.elapsed())
        return data

    def _fetch_api_unpaged(self, worker, etag, req_url, needs_auth, **kwargs):
        request, etag = self._fetch_api(
            worker, req_url, kwargs, etag, needs_auth)

        if not request or request.status_code >= 400:
            worker.stats().update(stats.Stats.REQUEST, total=1, failure=1)
            return (False, None, request.status_code if request else 403)

        if request.status_code == 304:
            worker.stats().update(stats.Stats.REQUEST, total=1)
            return (True, None, 304)

        worker.stats().update(stats.Stats.REQUEST, total=1, changed=1)
        return (True, request.json(), 200)

    def _fetch_api(self, worker, url, params, etag, needs_auth):
        headers = {
            'If-None-Match': etag,
            'User-Agent': self.__user_agent
        }

        if needs_auth:
            if not self.__access_token:
                worker.log().error("No auth token set for %s", url)
                return (None, "")
            headers['Authorization'] = 'Bearer ' + self.__access_token

        request = worker.session().get(url, params=params, headers=headers)

        try:
            request.raise_for_status()
        except Exception:
            worker.log().exception("API request error")
            return (request, "")

        if 'etag' in request.headers:
            etag = request.headers['etag']
        else:
            etag = ""

        return (request, etag)

class RegionalAPI(GlobalAPI):
    """
    ESI API endpoints for regional market data.
    """

    # The API endpoint for requesting NPC station information.
    __STATION_INFO  = 'https://esi.evetech.net/latest/universe/stations/{}/'

    # The API endpoint for requesting Player structure information
    __STRUCT_INFO   = 'https://esi.evetech.net/latest/universe/structures/{}/'

    # The API endpoint for requesting orders in a particular structure.
    __STRUCT_ORDERS = 'https://esi.evetech.net/latest/markets/structures/{}/'

    # The API endpoint for requesting orders in a region, optionally with
    # a specified item type ID filter
    __REGION_ORDERS = 'https://esi.evetech.net/latest/markets/{}/orders/'

    # The API endpoint for requesting the item type IDs wih active orders
    # in the specified region
    __REGION_TYPES  = 'https://esi.evetech.net/latest/markets/{}/types/'


    # The maxmimum valid station ID
    __STATION_MAX   = 69999999

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

        GlobalAPI.__init__(self, config)

        self.__location_cache = {}

        self.__order_page_lock = threading.Lock()
        self.__order_pages = {}

        self.__struct_page_lock = threading.Lock()
        self.__struct_pages = {}

        self.__type_page_lock = threading.Lock()
        self.__type_pages = {}

        self.__region_id = region_id

    def region_id(self):
        """
        Returns the region ID for this API instance
        """

        return self.__region_id

    def location_ids(self):
        """
        Returns the cached location ID list for this API instance.
        """

        return [loc for loc, valid in self.__location_cache if valid]

    def fetch_location_info(self, worker, location_id):
        """
        Returns structure or station info for the specified location ID.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            location_id: The station or structure ID to lookup.

        Returns:
            The info fields for the specified ID.
        """

        if location_id in self.__location_cache:
            return (None, True)

        if location_id <= self.__STATION_MAX:
            info = self.fetch_station_info(worker, location_id)
            if info:
                self.__location_cache[location_id] = False
                info['is_struct'] = False
            return (info, False)

        info = self.fetch_structure_info(worker, location_id)
        if not info:
            self.__location_cache[location_id] = False
            return (None, False)

        self.__location_cache[location_id] = True
        info['station_id'] = location_id
        info['system_id'] = info['solar_system_id']
        info['is_struct'] = True

        return (info, False)

    def fetch_station_info(self, worker, station_id):
        """
        Returns station info for the specified station ID.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            station_id: The station ID to lookup.

        Returns:
            The info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__STATION_INFO.format(station_id), False)

    def fetch_structure_info(self, worker, structure_id):
        """
        Returns player owned structure info for the specified sructure ID.
        This API call requires ESI authentication.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            station_id: The structure ID to lookup.

        Returns:
            The info fields for the specified ID.
        """

        return self._fetch_unpaged(
            worker, '', self.__STRUCT_INFO.format(structure_id), True)

    def fetch_structure_orders(self, worker, struct_id, callback=None):
        """
        Fetches orders for the specified structure ID.

        Args:
            worker: The marketwatch.worker.Worker containing local state.
            struct_id: The ID of the structure.
            callback: An optional callable to invoke for each order page.

        Returns:
            If not callback was specified, returns the list of market order
            pages, and the list of order IDs that were still cached.
        """

        return self.__fetch_paged(
            worker, callback, True, RegionalAPI.__fetch_struct_order_page, struct_id)

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
            worker, callback, False, RegionalAPI.__fetch_type_order_page, type_id)

    def fetch_types(self, worker):
        """
        Fetches the list of type IDs for the region

        Args:
            worker: The marketwatch.worker.Worker containing local state.

        Returns:
            The list of item type IDs available on the market in the
            region associated with this API instance.
        """

        return self.__fetch_paged(
            worker, None, False, RegionalAPI.__fetch_type_page)

    def __fetch_struct_order_page(self, worker, number, needs_auth, struct_id):
        with self.__struct_page_lock:
            if not struct_id in self.__struct_pages:
                struct_pages = self.__struct_pages[struct_id] = []
            else:
                struct_pages = self.__struct_pages[struct_id]

            if number > len(struct_pages):
                struct_page = self.Page(number)
                struct_pages.insert(number-1, struct_page)
            else:
                struct_page = struct_pages[number-1]

        req_url = self.__STRUCT_ORDERS.format(struct_id)
        max_pages, orders, status = self.__fetch_api_page(
            worker, struct_page, req_url, needs_auth)

        if orders:
            struct_page.cache = []
            for order in orders:
                struct_page.cache.append(int(order['order_id']))
            return (max_pages, orders, None, status)

        return (max_pages, orders, struct_page.cache, status)

    def __fetch_type_order_page(self, worker, number, needs_auth, type_id):
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
        max_pages, orders, status = self.__fetch_api_page(
            worker, order_page, req_url, needs_auth, type_id=type_id)

        if orders:
            order_page.cache = []
            for order in orders:
                order_page.cache.append(int(order['order_id']))
            return (max_pages, orders, None, status)

        return (max_pages, orders, order_page.cache, status)

    def __fetch_type_page(self, worker, number, needs_auth):
        with self.__type_page_lock:
            if number in self.__type_pages:
                type_page = self.__type_pages[number]
            else:
                type_page = self.Page(number)
                self.__type_pages[number] = type_page

        req_url = self.__REGION_TYPES.format(self.__region_id)
        max_pages, orders, status = self.__fetch_api_page(
            worker, type_page, req_url, needs_auth)
        return (max_pages, orders, None, status)

    def __fetch_paged(self, worker, callback, needs_auth, func, *args, **kwargs):
        current_page = 1
        num_errors = 0

        data_pages = []
        cache_pages = []
        with stats.Stats.Timer() as timer:
            while True:
                max_pages, data, cache, status = func(
                    self, worker, current_page, needs_auth, *args, **kwargs)

                if status >= 400 and status < 500:
                    return (None, None)

                if max_pages < 1:
                    if num_errors >= self._ERROR_RETRIES:
                        break

                    num_errors += 1
                    time.sleep(0.5*num_errors)
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

    def __fetch_api_page(self, worker, page, req_url, needs_auth, **kwargs):
        req_params = {'page': page.number}
        req_params.update(kwargs)

        request, etag = self._fetch_api(
            worker, req_url, req_params, page.etag, needs_auth)
        page.etag = etag

        if not request or request.status_code >= 400:
            worker.stats().update(stats.Stats.REQUEST, total=1, failure=1)
            return (-1, None, request.status_code)

        if 'x-pages' in request.headers:
            max_pages = int(request.headers['x-pages'])
        else:
            max_pages = 1

        if request.status_code == 304:
            worker.stats().update(stats.Stats.REQUEST, total=1)
            return (max_pages, None, request.status_code)

        worker.stats().update(stats.Stats.REQUEST, total=1, changed=1)
        return (max_pages, request.json(), request.status_code)
