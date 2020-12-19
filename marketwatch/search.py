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

import os

from whoosh.index import create_in, exists_in, open_dir
from whoosh.fields import NGRAMWORDS, STORED, Schema
from whoosh.highlight import WholeFragmenter
from whoosh.qparser import QueryParser

class SearchIndex():
    """
    Utility functions for accessing and creating a search index.
    """

    def __init__(self, config):
        """
        Creates a new search index instance from the specified config.

        Args:
            config: Config object that contains parameters for the index.
        """

        self.__built = False
        self.__index_dir = config['index_dir']

    def build_index(self, database, rebuild=False):
        """
        Builds a search index for the contents of the specified database.
        Currently only indexes item type names.

        Args:
            database: The database that contains data to index.
            rebuild: Optional arg that indicates whether to rebuild the index
        """

        os.makedirs(self.__index_dir, exist_ok=True)

        if exists_in(self.__index_dir) and not rebuild:
            index = open_dir(self.__index_dir)
        else:
            index = create_in(
                self.__index_dir,
                Schema(
                    name=NGRAMWORDS(queryor=True, maxsize=20, stored=True),
                    type_id=STORED))

        group_ids = database.get_groups()
        type_ids = []
        for group_id in group_ids:
            type_ids += database.get_group_types(group_id)

        writer = index.writer()
        for type_id in type_ids:
            type_info = database.get_type_info(type_id)
            writer.add_document(name=type_info['name'], type_id=type_info['id'])

        writer.commit()

    def search_index(self, search_string, limit=10):
        """
        Searches for the specified string in the index, if it has been
        created.

        Args:
            search_string: The string to search.
            limit: Optional limit on the number of results

        Returns:
            A list of (string, id) result pairs.
        """

        if not exists_in(self.__index_dir):
            return []

        index = open_dir(self.__index_dir)
        with index.searcher() as searcher:
            parser = QueryParser("name", schema=index.schema)
            query = parser.parse(search_string)
            results = searcher.search(query, limit=limit)
            results.fragmenter = WholeFragmenter()

            result_info = []
            for result in results:
                info = {
                    'name': result['name'],
                    'highlight': result.highlights('name'),
                    'id': result['type_id']
                }

                result_info.append(info)

            return result_info
