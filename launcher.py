#!/usr/bin/env python3

import mygoogleapiclient as mygoogleapiclient

import pathlib, sys, subprocess, sched, os, threading, re, socket, json, time, logging, websockets, asyncio, myreg
from googleapiclient.errors import HttpError
from ssl import SSLError
from threading import Thread
from datetime import datetime
from utils import str2SMH, build_result, build_status, row2List, to_time

LOOP = asyncio.get_event_loop()
logger = logging.getLogger("launcher")
logging.basicConfig(level=logging.INFO)

logging.getLogger("googleapiclient").setLevel(logging.WARNING)


working_dir= os.getenv("WORKING_DIRECTORY")
if working_dir:
    logger.info("Changing working directory to " + working_dir)
    os.chdir(working_dir)

player = socket.gethostname()
remote = '192.168.1.63'

if player == 'mcbk.local':
    player = 'manager'
    #remote = 'localhost'

retry_interval = 5
current_action = {'time': 0, 'args': []}
HISTORY = []
COMMANDS = myreg.get_value("commands")

QUEUE = sched.scheduler(time.time, time.sleep)

SETTINGS = {'uuid': None, 'name': player, 'service_port': 1301, 'server_port': 1300, 'reconnect_time': 2, 'remote': remote}
last_error = None
need_update = False
app = None
server = None
scope = None

class Scope(threading.local):
    def __init__(self, files, fileIds=[]):
        super().__init__()
        self.files = files
        self.commandsFileId = fileIds


####################################
#
# Global Methods  
#
####################################

def action_wrapper(cmd, *args):
    global HISTORY, LOOP
    HISTORY.append({'time': time.time(), 'args': [cmd] + args[0]})

    filename, file_extension = os.path.splitext(cmd)

    if not file_extension == '.py':
        cmd = cmd + '.py'

    data = args[1] if len(args)>1 else None

    if pathlib.Path(cmd).is_file():
        a = []
        a.insert(0, cmd)
        a.insert(0, "python")
        print(a)
        asyncio.ensure_future(run(' '.join(args[0]), data), loop = LOOP)
    else:
        if data:
            asyncio.ensure_future(run(data['command'], data), loop = LOOP)

async def run(cmd, data):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'{stdout.decode()}')
        r = stdout.decode()
        if server:
            await server.send(json.dumps(build_result(data['id'], r if isinstance(r, str) else r.decode("utf-8"), 'DONE')))

    if stderr:
        print(f'{stderr.decode()}')
        r = stderr.decode()
        if server:
            await server.send(json.dumps(build_result(data['id'], r if isinstance(r, str) else r.decode("utf-8"), 'DONE')))


def build_scope():
    global scope, player
    try:
        files = mygoogleapiclient.spreadsheets(player)
        fileIds = mygoogleapiclient.getFileIds(files, '(Responses)')
        scope = Scope(files, fileIds)
    except Exception as e:
        logger.exception(e)
    

def scheduler():
    while True:
        QUEUE.run(False)
        time.sleep(0.5)


def commands_update():
    global COMMANDS, scope
    while 1:
        if not scope:
            build_scope()
        if not scope or not scope.commandsFileId:
            return
        COMMANDS = mygoogleapiclient.getValues(scope.commandsFileId)
        if not COMMANDS or len(COMMANDS) < 1:
            return
        myreg.set_value("commands", COMMANDS)

        time.sleep(int(COMMANDS[1][4]))

old_hash = 0 
def commands_process():
    global QUEUE, COMMANDS, old_hash, scope
    while 1:
        if not COMMANDS or len(COMMANDS) < 1:
            continue
        new_hash = 0    
        for idx in range(2, len(COMMANDS)-1):
            for i in range(0, len(COMMANDS[idx])-1):
                new_hash += hash(COMMANDS[idx][i])

        if old_hash == new_hash:
            continue
        old_hash = new_hash
        clean_queue()
        for idx in range(2, len(COMMANDS)-1):
            row = COMMANDS[idx]
            processed_time = row[1]
            repeat_interval = row[2]
            cmd = row[3]

            if processed_time != "" and repeat_interval == "":
                continue
            if processed_time == "":
                QUEUE.enter(0, 1, action_wrapper, (cmd, row2List(row)))
                processed_time = update_processed_time(idx + 1)
            if repeat_interval != "":
                next_time = to_time(time, datetime, int(processed_time), repeat_interval)
                QUEUE.enter(next_time, 1, action_wrapper, (cmd, row2List(row)))

            print("Adding ", time.ctime(next_time+time.time()), repeat_interval, cmd, row2List(row))

        new_hash = 0 
        for idx in range(2, len(COMMANDS)-1):
            for i in range(0, len(COMMANDS[idx])-1):
                new_hash += hash(COMMANDS[idx][i])

        old_hash = new_hash
            
        time.sleep(5)


def update_processed_time(idx):
    global COMMANDS, scope
    tm = time.time()
    COMMANDS[idx][1] = tm
    if not scope:
        build_scope()
    if scope and scope.commandsFileId:
        try:
            mygoogleapiclient.update(mygoogleapiclient.sheets(), scope.commandsFileId, "Form responses 1!B{0}".format(idx), tm)
        except Exception as e:
            logger.exception(e)
    return tm


async def update_settings(settings, data):
    settings['uuid'] = data['uuid']
    if settings.get('service_port') != data['port']:
        settings['service_port'] = data['port']


def clean_queue():
    try:
        list(map(QUEUE.cancel, QUEUE.queue))
    except ValueError:
        print(time.strftime('%X'), 'Exception while cleaning Sched queue.')


def queue2json():
    global QUEUE
    result = []
    [result.append({'type': 'event', e._fields[0]: e[0], e._fields[1]: e[1], e._fields[3]: e[3]}) for e in QUEUE.queue]
    return result


def history2json():
    result = []
    [result.append(el) for el in HISTORY]
    return result


async def connect_client():
    global last_error, need_update, server, app, SETTINGS
    _settings = SETTINGS
    connection_string = 'ws://' + _settings['remote'] + ':' + str(_settings.get('server_port'))
    while True:
        try:
            logger.info("Connecting to remote: " + connection_string)
            async with websockets.connect(connection_string) as _server:
                server = _server
                logger.info("Connection established.")
                await server.send(json.dumps({'type': 'name', 'name': _settings['name']}))
                while True:
                    try:
                        msg = await server.recv()
                        data = json.loads(msg)
                        if data['type'] == "settings":
                            await update_settings(_settings, data)
                        elif data['type'] == "command":
                            cmd = data['command']
                            logger.info(data)
                            args = re.sub("[^\w-]", " ",  cmd).split()
                            user = re.findall(r'"(.*?)"', cmd)
                            if user:
                                _tmp = cmd.split('"')
                                args = [_tmp[0], user[0]]
                                for i in range(2, len(_tmp)):
                                    args += _tmp[i].strip().split(' ')

                            cmd = args.pop(0).strip()

                            if cmd == 'reload-data':
                                need_update = True
                            elif cmd == 'status':
                                await server.send(json.dumps(build_status(data['id'], {'queue': queue2json(), 'history': history2json()})))
                            elif cmd == 'restart-thread':
                                startLauncher()
                            elif cmd == 'clean-queue':
                                clean_queue()
                            else:
                                QUEUE.enterabs(0, 1, action_wrapper, (cmd, args, data))
                                await server.send(json.dumps(build_result(data['id'], '', 'QUEUED')))
                                
                    except websockets.ConnectionClosed as cc:
                        logger.info("Connection Closed.")
                        break    
                    except Exception as ee:
                        logger.exception(ee)
                        break
        except Exception as e:
            if last_error != str(e):
                logger.exception(e)
            logger.info("Disconnected from remote: " + connection_string + ". Reconnecting in " + str(
                _settings.get('reconnect_time')) + "s.")
            last_error = str(e)
            time.sleep(_settings.get('reconnect_time'))

def show_queue():
    while 1:
        result = []
        [result.append(e[3]) for e in QUEUE.queue]
        print(result)
        time.sleep(1)

def startLauncher():
    global LOOP
    threads = [
        Thread(name="scheduler", target=scheduler, daemon=True),
        # Thread(name="commands_update", target=commands_update, daemon=True),
        Thread(name="commands_process", target=commands_process, daemon=True),
        # Thread(name="show_queue", target=show_queue, daemon=True)
    ]

    [th.start() for th in threads]
    while True:
        LOOP.run_until_complete(connect_client())


if __name__ == "__main__":
    startLauncher()
