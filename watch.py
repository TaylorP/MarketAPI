import argparse
import configparser
import daemon

from marketwatch import redis, watcher

def run_watcher(config):
    w = watcher.Watcher(config)
    w.watch()

parser = argparse.ArgumentParser(description='EVE market order watcher')
parser.add_argument(
    '-c', '--config', dest='config', required=True,
    help='The path to an INI file containing configuration options')
parser.add_argument(
    '-d', '--daemon', dest='daemon', required=False, action='store_true',
    help='Whether or not the watcher script should run in the background')
args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.config)

if args.daemon:
    with daemon.DaemonContext(working_directory='.') as context:
        run_watcher(config)
else:
    run_watcher(config)
