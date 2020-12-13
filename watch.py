import daemon

from config import CONFIG
from marketwatch import redis, watcher

def run_watcher():
    w = watcher.Watcher(CONFIG)
    w.watch()

if CONFIG['daemonize']:
    with daemon.DaemonContext(working_directory='.') as context:
        run_watcher()
else:
    run_watcher()
