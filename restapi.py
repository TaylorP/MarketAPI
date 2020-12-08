import config

from fastapi import FastAPI
from marketwatch import database

app = FastAPI()

@app.get("/market/orders/{type_id}")
def allOrders(type_id: int):
    conn = database.Database.instance(config.CONFIG)
    orders = []
    for region_id in config.CONFIG['regions']:
        orders += conn.get_orders(region_id, type_id)
    return orders

@app.get("/market/orders/{type_id}/{region_id}")
def regionOrders(type_id: int, region_id: int):
    conn = database.Database.instance(config.CONFIG)
    return conn.get_orders(region_id, type_id)
