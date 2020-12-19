from marketwatch import redis

CONFIG = {
    "db_type"       : redis.RedisDatabase,
    "db_opts"       : {
        "host"          : "localhost",
        "port"          : 6379,
        "database"      : 0,
        "enabled"       : False
    },

    "pool_size"     : 4,
    "fetch_delay"   : 600,
    "wait_delay"    : 30,
    "static_time"   : "11:30",
    "daemonize"     : False,

    "fetch_regions" : False,
    "fetch_groups"  : False,
    "fetch_orders"  : False,
    "build_index"   : True,

    "index_dir"     : "./search",

    "log_dir"       : "./logs",
    "log_size"      : 65536,
    "log_count"     : 5,
    "log_shell"     : True,

    "agent"         : "mcsheepeater/marketwatch 1.0",
}
