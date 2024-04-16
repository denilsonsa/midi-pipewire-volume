from queue import Queue
from threading import Thread

from .pypewyre import PWDump, PWState

# pip install 'mido[ports-rtmidi]'
import mido
#print(mido.backend)
# If this backend doesn't work for you, try another one:
# https://mido.readthedocs.io/en/stable/backends/index.html#choice


def pw_dump_producer(q:Queue):
    p = PWDump()
    for obj in p.blocking_generator():
        q.put(("pw", obj))


def midi_producer(ports, q:Queue):
    for (port, msg) in mido.ports.multi_receive(ports, yield_ports=True, block=True):
        q.put(("midi", port, msg))


def main():
    # Both threads put events into this queue.
    main_queue = Queue()

    # A local copy of the PipeWire server state.
    pw_state = PWState()

    # pw-dump --monitor
    pw_thread = Thread(daemon=True, target=pw_dump_producer, args=(main_queue,))

    # MIDI
    # TODO: Make the list of ports dynamic. You know, when MIDI devices get connected and disconnected.
    midi_ports = [
        mido.open_input(name)
        for name in mido.get_input_names()
    ]
    midi_thread = Thread(daemon=True, target=midi_producer, args=(midi_ports, main_queue))

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
            case _:
                raise ValueError("Invalid item in the main_queue: {!r}".format(item))
