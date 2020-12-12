import config
from marketwatch import redis, watcher

w = watcher.Watcher(config.CONFIG)
w.watch()
