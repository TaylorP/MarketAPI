import configparser

from typing import List, Optional
from urllib.parse import unquote

from fastapi import FastAPI, Response
from marketwatch import database
from marketwatch import search

app = FastAPI()

config = configparser.ConfigParser()
config.read("config.ini")

@app.get("/universe/regions")
def regions(response: Response):
    conn = database.Database.instance(config)

    cache_expiry = conn.get_universe_cache_expiry()
    if cache_expiry:
        response.headers['Last-Modified'] = cache_expiry['modify']
        response.headers['Expires'] = cache_expiry['expire']

    region_ids = conn.get_regions()
    regions = []
    for region_id in region_ids:
        regions.append(conn.get_region_info(region_id))

    return regions

@app.get("/universe/systems/{region_id}")
def systems(response: Response, region_id: int):
    conn = database.Database.instance(config)

    cache_expiry = conn.get_universe_cache_expiry()
    if cache_expiry:
        response.headers['Last-Modified'] = cache_expiry['modify']
        response.headers['Expires'] = cache_expiry['expire']

    system_ids = conn.get_systems(region_id)
    systems = []
    for system_id in system_ids:
        systems.append(conn.get_system_info(system_id))

    return systems

@app.get("/universe/locations/{region_id}")
def locations(region_id: int):
    conn = database.Database.instance(config)
    location_ids = conn.get_locations(region_id)
    locations = []
    for location_id in location_ids:
        locations.append(conn.get_location_info(location_id))
    return locations

@app.post("/universe/locations")
def locations(location_ids: List[int]):
    conn = database.Database.instance(config)
    locations = []
    for location_id in location_ids:
        location_info = conn.get_location_info(location_id)
        if location_info:
            locations.append(location_info)
    return locations

@app.get("/universe/location/{location_id}")
def location(location_id: int):
    conn = database.Database.instance(config)
    return conn.get_location_info(location_id)

@app.get("/universe/types")
def types(response: Response):
    conn = database.Database.instance(config)

    cache_expiry = conn.get_universe_cache_expiry()
    if cache_expiry:
        response.headers['Last-Modified'] = cache_expiry['modify']
        response.headers['Expires'] = cache_expiry['expire']

    return conn.get_types()

@app.get("/universe/type/{type_id}")
def type(response: Response, type_id: int):
    conn = database.Database.instance(config)

    cache_expiry = conn.get_universe_cache_expiry()
    if cache_expiry:
        response.headers['Last-Modified'] = cache_expiry['modify']
        response.headers['Expires'] = cache_expiry['expire']
    
    return conn.get_type_info(type_id)

@app.get("/market/groups")
def groups(response: Response):
    conn = database.Database.instance(config)

    cache_expiry = conn.get_market_group_cache_expiry()
    if cache_expiry:
        response.headers['Last-Modified'] = cache_expiry['modify']
        response.headers['Expires'] = cache_expiry['expire']

    group_ids = conn.get_groups()
    groups = []
    for group_id in group_ids:
        groups.append(conn.get_group_info(group_id))

    return groups

@app.get("/market/group/{group_id}")
def group_types(response: Response, group_id: int):
    conn = database.Database.instance(config)

    cache_expiry = conn.get_market_group_cache_expiry()
    if cache_expiry:
        response.headers['Last-Modified'] = cache_expiry['modify']
        response.headers['Expires'] = cache_expiry['expire']

    type_ids = conn.get_group_types(group_id)
    types = []
    for type_id in type_ids:
        types.append(conn.get_type_info(type_id))

    return types

@app.get("/search/{search_type}")
def search_types(search_type: int, query: Optional[str]="", pid: Optional[int]=0):
    if not query:
        return []

    index = search.SearchIndex(config)
    return index.search(search.SearchIndex.Type(search_type), query, pid, 15)

@app.get("/market/orders/{type_id}")
def orders(type_id: int):
    conn0 = database.Database.instance(config, 0)
    conn1 = database.Database.instance(config, 0)
    regions = conn0.get_regions()

    orders = []
    for region_id in regions:
        conn1.get_orders(region_id, type_id, orders=orders)
    return orders

@app.get("/market/orders/{type_id}/{region_id}")
def region_orders(type_id: int, region_id: int):
    conn = database.Database.instance(config, 0)
    return conn.get_orders(region_id, type_id)

@app.get("/market/orders/{type_id}/{region_id}/{system_id}")
def system_orders(type_id: int, region_id: int, system_id: int):
    conn = database.Database.instance(config, 0)
    return conn.get_orders(region_id, type_id, system_id)
