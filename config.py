from marketwatch import redis

CONFIG = {
    "db_type"   : redis.RedisDatabase,
    "db_opts"   : {
        "host"      : "localhost",
        "port"      : 6379,
        "database"  : 0,
        "enabled"   : False
    },

    "pool_size" : 1,
    "min_time"  : 600,

    "log_dir"   : "./logs",
    "log_size"  : 65536,
    "log_count" : 5,
    "log_shell" : True,

    "agent"     : "mcsheepeater/marketwatch 1.0",

    "regions": [
        10000001, 10000002, 10000003, 10000004, 10000005, 10000006, 10000007,
        10000008, 10000009, 10000010, 10000011, 10000012, 10000013, 10000014,
        10000015, 10000016, 10000017, 10000018, 10000019, 10000020, 10000021,
        10000022, 10000023, 10000025, 10000027, 10000028, 10000029, 10000030,
        10000031, 10000032, 10000033, 10000034, 10000035, 10000036, 10000037,
        10000038, 10000039, 10000040, 10000041, 10000042, 10000043, 10000044,
        10000045, 10000046, 10000047, 10000048, 10000049, 10000050, 10000051,
        10000052, 10000053, 10000054, 10000055, 10000056, 10000057, 10000058,
        10000059, 10000060, 10000061, 10000062, 10000063, 10000064, 10000065,
        10000066, 10000067, 10000068, 10000069, 10000070
    ]
}
