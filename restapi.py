import config

from fastapi import FastAPI
from marketwatch import database

app = FastAPI()

@app.get("/market/groups")
def groups():
    conn = database.Database.instance(config.CONFIG)
    return conn.get_groups()

@app.get("/market/group/{group_id}")
def group(group_id: int):
    conn = database.Database.instance(config.CONFIG)
    return conn.get_group_info(group_id)

@app.get("/market/allgroups/")
def allGroup():
    conn = database.Database.instance(config.CONFIG)
    group_ids = conn.get_groups()
    groups = []
    for group_id in group_ids:
        groups.append(conn.get_group_info(group_id))
    return groups

@app.get("/market/orders/{type_id}")
def orders(type_id: int):
    conn = database.Database.instance(config.CONFIG)
    orders = []
    for region_id in config.CONFIG['regions']:
        orders += conn.get_orders(region_id, type_id)
    return orders

@app.get("/market/orders/{type_id}/{region_id}")
def region_orders(type_id: int, region_id: int):
    conn = database.Database.instance(config.CONFIG)
    return conn.get_orders(region_id, type_id)
