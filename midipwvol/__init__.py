import sys

from queue import Queue
from threading import Thread

from .ddcutil_service import DdcutilInterface
from .pypewyre import PWDump, PWState, PWQueryResult

# pip install xdg-base-dirs
from xdg_base_dirs import xdg_config_home

# pip install 'mido[ports-rtmidi]'
import mido
#print(mido.backend)
# If this backend doesn't work for you, try another one:
# https://mido.readthedocs.io/en/stable/backends/index.html#choice


def pw_dump_producer(q:Queue):
    # This function runs in a separate thread.
    p = PWDump()
    for obj in p.blocking_generator():
        q.put(("pw", obj))


def midi_producer(ports, q:Queue):
    # This function runs in a separate thread.
    for (port, msg) in mido.ports.multi_receive(ports, yield_ports=True, block=True):
        q.put(("midi", port, msg))


def main():
    # Try loading custom config from ~/.config/midipwvol/
    sys.path.insert(0, xdg_config_home() / "midipwvol")
    import midipwvolconfig

    # Both threads put events into this queue.
    main_queue = Queue()

    # -- Pipewire --
    # A local copy of the PipeWire server state.
    pw_state = PWState()

    def pw(**filters):
        # Inspired by jQuery.
        # Receives filters, returns a magic PWQueryResult.
        # Closure: encapsulates the pw_state variable.
        return PWQueryResult(pw_state, pw_state.query_all(**filters))

    # pw-dump --monitor
    pw_thread = Thread(daemon=True, target=pw_dump_producer, args=(main_queue,))

    # -- MIDI --
    # TODO: Make the list of ports dynamic. You know, when MIDI devices get connected and disconnected.
    midi_ports = [
        mido.open_input(name)
        for name in mido.get_input_names()
    ]
    midi_thread = Thread(daemon=True, target=midi_producer, args=(midi_ports, main_queue))

    # -- ddcutil-service --
    # Initializing the proxy object:
    ddc = DdcutilInterface(service_name="com.ddcutil.DdcutilService", object_path="/com/ddcutil/DdcutilObject")

    pw_thread.start()
    midi_thread.start()

    while True:
        item = main_queue.get()
        match item:
            case ("pw", "RESET"):
                # print("pw RESET!")
                pw_state.update("RESET")
            case ("pw", objs):
                # print("pw list of size ", len(objs))
                pw_state.update(objs)
                # print("state size:", len(pw_state.db))
            case ("midi", port, msg):
                print("midi from", port, " => ", msg)
                midipwvolconfig.handle_midi_message(port=port, message=msg, pw=pw, ddc=ddc)
            case _:
                raise ValueError("Invalid item in the main_queue: {!r}".format(item))
