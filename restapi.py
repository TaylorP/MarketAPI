from typing import List

from fastapi import FastAPI
from marketwatch import database

import config

app = FastAPI()

@app.get("/universe/regions")
def regions():
    conn = database.Database.instance(config.CONFIG)
    region_ids = conn.get_regions()
    regions = []
    for region_id in region_ids:
        regions.append(conn.get_region_info(region_id))
    return regions

@app.get("/universe/systems/{region_id}")
def systems(region_id: int):
    conn = database.Database.instance(config.CONFIG)
    system_ids = conn.get_systems(region_id)
    systems = []
    for system_id in system_ids:
        systems.append(conn.get_system_info(system_id))
    return systems

@app.get("/universe/locations/{region_id}")
def locations(region_id: int):
    conn = database.Database.instance(config.CONFIG)
    location_ids = conn.get_locations(region_id)
    locations = []
    for location_id in location_ids:
        locations.append(conn.get_location_info(location_id))
    return locations

@app.post("/universe/locations")
def locations(location_ids: List[int]):
    conn = database.Database.instance(config.CONFIG)
    locations = []
    for location_id in location_ids:
        location_info = conn.get_location_info(location_id)
        if location_info:
            locations.append(location_info)
    return locations

@app.get("/universe/location/{location_id}")
def location(location_id: int):
    conn = database.Database.instance(config.CONFIG)
    return conn.get_location_info(location_id)

@app.get("/market/groups")
def groups():
    conn = database.Database.instance(config.CONFIG)
    return conn.get_groups()

@app.get("/market/orders/{type_id}")
def orders(type_id: int):
    conn = database.Database.instance(config.CONFIG)
    regions = conn.get_regions()

    orders = []
    for region_id in regions:
        conn.get_orders(region_id, type_id, orders)
    return orders

@app.get("/market/orders/{type_id}/{region_id}")
def region_orders(type_id: int, region_id: int):
    conn = database.Database.instance(config.CONFIG)
    return conn.get_orders(region_id, type_id)

