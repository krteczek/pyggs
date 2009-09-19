# -*- coding: utf-8 -*-
"""
    plugins/cache.py - handles global database of cache details.
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

import logging
import math
import time

from . import base
from pyggs import Storage


class Plugin(base.Plugin):
    def __init__(self, master):
        base.Plugin.__init__(self, master)
        self.about = _("Global storage for detailed info about caches.")


    def setup(self):
        config = self.master.config

        config.assertSection(self.NS)
        config.defaults[self.NS] = {}
        config.defaults[self.NS]["timeout"] = "14"
        config.update(self.NS, "timeout", _("'Cache' details data timeout in days"))


    def prepare(self):
        base.Plugin.prepare(self)

        self.homecoord = {}
        self.homecoord["lat"] = float(self.master.config.get("general", "homelat"))
        self.homecoord["lon"] = float(self.master.config.get("general", "homelon"))

        self.master.registerHandler("cache", self.parseCache)
        self.storage = CacheDatabase(self, self.master.globalStorage)


    def parseCache(self, cache):
        """Update Cache database"""
        details = cache.getDetails()
        self.log.info("Updating Cache database for {0}: {1}.".format(details.get("waypoint"), details.get("name")))
        self.storage.update(details)


    def distance(self, lat1, lon1, lat2 = None, lon2 = None):
        """Calculate distance from home coordinates"""
        if lat2 is None:
            lat2 = self.homecoord["lat"]
        if lon2 is None:
            lon2 = self.homecoord["lon"]

        lon1 = math.radians(lon1)
        lat1 = math.radians(lat1)
        lon2 = math.radians(lon2)
        lat2 = math.radians(lat2)
        d_lon = lon1 - lon2
        dist = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(d_lon)
        dist = math.acos(dist) * 6371
        return dist



class CacheDatabase(Storage):
    def __init__(self, plugin, database):
        self.NS = plugin.NS + ".db"
        self.log = logging.getLogger("Pyggs." + self.NS)
        self.plugin = plugin
        self.filename = database.filename

        self.createTables()


    def createTables(self):
        """If Cache table doesn't exist, create it"""
        db = self.getDb()
        db.execute("""CREATE TABLE IF NOT EXISTS cache (
                guid varchar(36) NOT NULL,
                waypoint varchar(9) NOT NULL,
                name varchar(255) NOT NULL,
                owner varchar(100) NOT NULL,
                owner_id varchar(36) NOT NULL,
                hidden date NOT NULL,
                type varchar(30) NOT NULL,
                country varchar(100) NOT NULL,
                province varchar(100) NOT NULL,
                lat decimal(9,6) NOT NULL,
                lon decimal(9,6) NOT NULL,
                difficulty decimal(2,1) NOT NULL,
                terrain decimal(2,1) NOT NULL,
                size varchar(15) NOT NULL,
                disabled int(1) NOT NULL,
                archived int(1) NOT NULL,
                hint text,
                attributes text,
                lastCheck date NOT NULL,
                PRIMARY KEY (guid),
                UNIQUE (waypoint))""")
        db.execute("""CREATE TABLE IF NOT EXISTS cache_visits (
                guid varchar(36) NOT NULL,
                type varchar(30) NOT NULL,
                count int(4),
                PRIMARY KEY (guid,type))""")
        db.execute("""CREATE TABLE IF NOT EXISTS cache_inventory (
                guid varchar(36) NOT NULL,
                tbid varchar(36) NOT NULL,
                name varchar(100) NOT NULL,
                PRIMARY KEY (guid,tbid))""")
        db.close()


    def update(self, data):
        """Update Cache database by data"""
        if "guid" not in data:
            self.log.debug("No guid passed, not updating.")
            return

        db = self.getDb()
        cur = db.cursor()
        cur.execute("SELECT * FROM cache WHERE guid=?", (data["guid"],))
        if (len(cur.fetchall()) > 0):
            exists = True
        else:
            exists = False

        cur.execute("DELETE FROM cache_inventory WHERE guid = ?", (data["guid"],))
        if len(data) > 1:
            for tbid in data["inventory"]:
                cur.execute("INSERT INTO cache_inventory(guid, tbid, name) VALUES(?,?,?)", (data["guid"], tbid, data["inventory"][tbid]))
            cur.execute("DELETE FROM cache WHERE guid = ?", (data["guid"],))
            cur.execute("INSERT INTO cache(guid, waypoint, name, owner, owner_id, hidden, type, country, province, lat, lon, difficulty, terrain, size, disabled, archived, hint, attributes, lastCheck) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (data["guid"], data["waypoint"], data["name"], data["owner"], data["owner_id"], data["hidden"], data["type"], data["country"], data["province"], data["lat"], data["lon"], data["difficulty"], data["terrain"], data["size"], data["disabled"], data["archived"], data["hint"], data["attributes"], time.time()))
            cur.execute("DELETE FROM cache_visits WHERE guid = ?", (data["guid"],))
            for logtype in data["visits"]:
                cur.execute("INSERT INTO cache_visits(guid, type, count) VALUES(?,?,?)", (data["guid"], logtype, data["visits"][logtype]))
        else:
            if exists:
                cur.execute("UPDATE cache SET lastCheck = ? WHERE guid = ?", (time.time(), data["guid"]))
            else:
                cur.execute("INSERT INTO cache(guid,lastCheck) VALUES(?,?)", (data["guid"],time.time()))
        db.commit()
        db.close()
        self.setEnv(self.NS + ".lastcheck", time.time())


    def select(self, guids):
        """Selects data from database, performs update if neccessary"""
        timeout = int(self.plugin.master.config.get(self.plugin.NS, "timeout"))*24*3600
        result = []
        db = self.getDb()
        cur = db.cursor()
        for guid in guids:
            row = cur.execute("SELECT * FROM cache WHERE guid = ?", (guid,)).fetchone()
            if row is None or (timeout + float(row["lastCheck"])) <= time.time():
                self.log.debug("Data about guid '{0}' out of date, initiating refresh.".format(guid))
                self.plugin.master.parse("cache", guid=guid)
                row = cur.execute("SELECT * FROM cache WHERE guid = ?", (guid,)).fetchone()
            row = dict(row)
            row["lat"] = float(row["lat"])
            row["lon"] = float(row["lon"])
            row["inventory"] = {}
            for inv in cur.execute("SELECT tbid, name FROM cache_inventory WHERE guid = ?", (guid,)).fetchall():
                row["inventory"][inv["tbid"]] = inv["name"]
            row["visits"] = {}
            for vis in cur.execute("SELECT type, count FROM cache_visits WHERE guid = ?", (guid,)).fetchall():
                row["visits"][vis["type"]] = int(vis["count"])
            result.append(row)
        db.close()

        return result
