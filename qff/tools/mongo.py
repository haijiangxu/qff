# coding :utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2019 XuHaiJiang/QFF
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os

import pymongo

from qff.tools.config import get_config

DEFAULT_DB_URI = 'mongodb://{}'.format(os.getenv('MONGODB', 'localhost'))
DB_NAME = 'qff'


class DbClient:

    def __init__(self, uri=None):
        if uri is not None:
            self.mongo_uri = uri
        else:
            self.mongo_uri = get_config('MONGODB', 'uri', default_value=DEFAULT_DB_URI)

    @property
    def client(self):
        return pymongo.MongoClient(self.mongo_uri)


MONGO_CLIENT = DbClient()
DATABASE = MONGO_CLIENT.client[DB_NAME]