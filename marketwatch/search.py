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
Item type name search index
"""

from enum import Enum
import os

from whoosh.index import create_in, exists_in, open_dir
from whoosh.fields import NGRAMWORDS, NUMERIC, STORED, Schema
from whoosh.highlight import WholeFragmenter
from whoosh.qparser import QueryParser
from whoosh.query import NumericRange

class SearchIndex():
    """
    Utility functions for accessing and creating a search index.
    """

    class Type(Enum):
        """
        Enumeration of the different type of search domains.
        """
        # Search index for region names
        REGION  = 0

        # Search index for system names
        SYSTEM  = 1

        # Search index for item type names
        TYPE    = 2

    def __init__(self, config):
        """
        Creates a new search index instance from the specified config.

        Args:
            config: Config object that contains parameters for the index.
        """

        self.__built = False
        self.__index_dir = config.get('search', 'index')

    def build_index(self, database, rebuild=False):
        """
        Builds a search index for the contents of the specified database.
        Currently only indexes item type names.

        Args:
            database: The database that contains data to index.
            rebuild: Optional arg that indicates whether to rebuild the index
        """

        os.makedirs(self.__index_dir, exist_ok=True)
        self.__create_region_index(database, rebuild)
        self.__create_type_index(database, rebuild)

    def search(self, search_type, search_string, pid=0, limit=10):
        """
        Searches for the specified string in the index, if it has been
        created.

        Args:
            search_string: The string to search.
            limit: Optional limit on the number of results

        Returns:
            A list of (string, id) result pairs.
        """

        if not exists_in(self.__index_dir, search_type.name):
            return []

        index = open_dir(self.__index_dir, search_type.name)
        with index.searcher() as searcher:
            parser = QueryParser("name", schema=index.schema)
            query = parser.parse(search_string)
            if pid:
                parent_filter = NumericRange("pid", pid, pid)
            else:
                parent_filter = None
            results = searcher.search(query, filter=parent_filter, limit=limit)
            results.fragmenter = WholeFragmenter()

            result_info = []
            for result in results:
                info = {
                    'name': result['name'],
                    'highlight': result.highlights('name'),
                    'id': result['id']
                }

                result_info.append(info)

            return result_info

    def __create_region_index(self, database, rebuild):
        index = self.__create_index(self.Type.REGION, rebuild)
        region_ids = database.get_regions()

        writer = index.writer()
        for region_id in region_ids:
            region_info = database.get_region_info(region_id)
            writer.add_document(
                name=region_info['name'],
                id=region_info['id'])
        writer.commit()

        index = self.__create_index(self.Type.SYSTEM, rebuild)

        writer = index.writer()
        for region_id in region_ids:
            system_ids = database.get_systems(region_id)
            for system_id in system_ids:
                system_info = database.get_system_info(system_id)
                writer.add_document(
                    name=system_info['name'],
                    id=system_info['id'],
                    pid=region_id)
        writer.commit()

    def __create_type_index(self, database, rebuild):
        index = self.__create_index(self.Type.TYPE, rebuild)

        type_ids = []
        for group_id in database.get_groups():
            type_ids += database.get_group_types(group_id)

        writer = index.writer()
        for type_id in type_ids:
            type_info = database.get_type_info(type_id)
            writer.add_document(
                name=type_info['name'],
                id=type_info['id'])
        writer.commit()

    def __create_index(self, index_entry, rebuild):
        index_name = index_entry.name
        if exists_in(self.__index_dir, index_name) and not rebuild:
            return open_dir(self.__index_dir, index_name)

        schema = Schema(
            name=NGRAMWORDS(queryor=True, maxsize=20, stored=True),
            id=STORED,
            pid=NUMERIC(signed=False, default=0))
        return create_in(self.__index_dir, schema, index_name)
