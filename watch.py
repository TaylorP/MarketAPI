import daemon

from config import CONFIG
from marketwatch import redis, watcher

with daemon.DaemonContext(working_directory='.') as context:
    w = watcher.Watcher(CONFIG)
    w.watch()
