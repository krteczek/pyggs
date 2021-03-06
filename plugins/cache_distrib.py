# -*- coding: utf-8 -*-
"""
    plugins/cache_distrib.py - Tables with distribution of finds by type,
      container and country.
    Copyright (C) 2009 Petr Morávek

    This file is part of Pyggs.

    Pyggs is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    Pyggs is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

from collections import OrderedDict

from . import base


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.dependencies = ["stats", "myfinds", "cache"]
        self.about = _("Statistics of found caches by type, size and country.")


    def prepare(self):
        base.Plugin.prepare(self)
        self.fetchAssoc = self.master.globalStorage.fetchAssoc


    def run(self):
        myFinds = self.myfinds.storage.getList()
        caches = self.cache.storage.getDetails(myFinds)

        templateData = {}
        templateData["total"] = len(myFinds)
        templateData["countries"] = self.getCountries(caches)
        templateData["types"] = self.getTypes(caches)
        templateData["sizes"] = self.getSizes(caches)
        self.stats.registerTemplate(":stats.cache_distrib", templateData)


    def getCountries(self, caches):
        result = self.fetchAssoc(caches, "country,#")
        tmp = []
        for country in result:
            if country == "":
                continue
            tmp.append({"country":country, "count":len(result[country])})
        tmp.sort(key=lambda x: x["count"], reverse=True)
        countries = OrderedDict()
        for row in tmp:
            countries[row["country"]] = row["count"]
        return countries


    def getTypes(self, caches):
        result = self.fetchAssoc(caches, "type,#")
        tmp = []
        for type in result:
            if type == "":
                continue
            tmp.append({"type":type, "count":len(result[type])})
        tmp.sort(key=lambda x: x["count"], reverse=True)
        types = OrderedDict()
        for row in tmp:
            types[row["type"]] = row["count"]
        return types


    def getSizes(self, caches):
        result = self.fetchAssoc(caches, "size,#")
        tmp = []
        for size in result:
            tmp.append({"size":size, "count":len(result[size])})
        tmp.sort(key=lambda x: x["count"], reverse=True)
        sizes = OrderedDict()
        for row in tmp:
            sizes[row["size"]] = row["count"]
        return sizes
