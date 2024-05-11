"""Simple Python module to interface with PipeWire.

This is not an official binding, and it is limited in many ways.
But it works for the purposes of this project, and might work for you too.

If you want a proper Python binding for PipeWire, please look at:
https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/1654
"""


import json
import os
import re
import select
import subprocess
import types

from collections import abc
from functools import cached_property
from threading import RLock

# For debugging:
from pprint import pprint


# There is a cubic formula between the internal PipeWire volume and the user-facing volume:
# https://github.com/PipeWire/wireplumber/blob/master/modules/module-mixer-api.c
# (search for `volume_from_linear` and `volume_to_linear`)
#
# For convenience, these two functions also support receiving a list.

def volume_from_linear(volume):
    if isinstance(volume, (int, float)):
        if volume <= 0:
            return 0
        return volume ** 3
    else:
        return [volume_from_linear(x) for x in volume]


def volume_to_linear(volume):
    if isinstance(volume, (int, float)):
        if volume <= 0:
            return 0
        return volume ** (1 / 3)
    else:
        return [volume_to_linear(x) for x in volume]


class PWDump:
    def __init__(self, pwdump_path:str="pw-dump"):
        """Creates the object, but doesn't launch anything yet.
        """
        self.pwdump_path = pwdump_path

        # We need the raw_decode() method from a JSONDecoder().
        self.decoder = json.JSONDecoder()
        # The child process.
        self.proc = None
        # The unprocessed stdout buffer.
        self.buffer = ""
        # If the buffer was reset, we should send a "RESET" message.
        self.buffer_was_reset = True

    def __repr__(self):
        return "<PWDump({!r}) pid={} fileno={}>".format(
            self.pwdump_path,
            self.proc.pid if self.proc else 'None',
            self.proc.stdout.fileno() if self.proc else 'None',
        )

    def _run(self):
        """Runs the external tool, and leaves it running in the background.
        """
        self.terminate()
        self.proc = subprocess.Popen(
            [self.pwdump_path, "--monitor"],
            stdout=subprocess.PIPE,
            # Default buffer size is just 8KB, which is not enough.
            bufsize=1024*1024,
            pipesize=1024*1024,
            # Since we're making this unbuffered, we cannot rely on Python's built-in automatic text decoding.
            text=False,
        )
        os.set_blocking(self.proc.stdout.fileno(), False)
        self.buffer = ""
        self.buffer_was_reset = True

    def _run_if_needed(self):
        """Runs the external tool if not yet running.

        Also re-runs the tool in case it was terminated.
        """
        # Process isn't running:
        if self.proc is None:
            self._run()
        # Process was running, but isn't anymore:
        if self.proc.poll() is not None:
            self._run()

    def fileno(self):
        """Returns the fileno of the pipe.

        This method is useful for using this object in `select.select()`.
        """
        self._run_if_needed()
        return self.proc.stdout.fileno()

    def __del__(self):
        """Basic auto-cleanup method.

        May not work all the time, though. Consider manually calling `.terminate()` or using inside a `with` context manager.
        """
        self.terminate()

    def close(self):
        """Alias for terminate().
        """
        self.terminate()

    def terminate(self):
        """Terminates/kills the background process.
        """
        if self.proc:
            # Sending the SIGTERM signal.
            self.proc.terminate()
            # Closing the pipe to prevent any further data.
            self.proc.stdout.close()

            try:
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired as e:
                # Sending the SIGKILL signal.
                self.proc.kill()

            try:
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired as e:
                # Waited for too long, not gonna block this Python code any further.
                # This may leave a zombie process around. Sorry.
                pass

    def __enter__(self):
        """For usage inside `with` context manager.
        """
        self._run_if_needed()
        return self

    def __exit__(self, *args, **kwargs):
        """For usage inside `with` context manager.
        """
        self.terminate()

    def __iter__(self):
        """This object is iterable.
        """
        return self

    def __next__(self):
        """Returns the next JSON object.

        Non-blocking, keeps yielding until no further data is available.
        Calling it again later may yield more objects.
        """
        self._run_if_needed()

        if self.buffer_was_reset:
            self.buffer_was_reset = False
            return "RESET"

        # Concatenate previous buffer with the new data.
        # New data is found by reading bytes until we get None
        self.buffer += b"".join(iter(self.proc.stdout.read, None)).decode("utf8")
        if len(self.buffer) == 0:
            raise StopIteration()

        try:
            data, index = self.decoder.raw_decode(self.buffer)
        except json.JSONDecodeError as e:
            # Sanity check, to prevent memory leak.
            assert len(self.buffer) < 1024 * 1024 * 16
            # Assuming the error is due to incomplete JSON.
            raise StopIteration()
        # Updating the buffer, skipping the already parsed data.
        # raw_decode doesn't like leading whitespace.
        self.buffer = self.buffer[index:].lstrip()
        return data

    def blocking_generator(self, timeout=None):
        """This is a blocking generator that blocks until more data is available.

        Without any timeout, it is an infinite generator that never ends.
        """
        while True:
            ready, _, _ = select.select([self], [], [], timeout)
            if len(ready) == 0:
                return
            yield from self


class PWObject:
    """Convenience object, to make it easy to access some relevant fields.
    """
    def __init__(self, obj):
        self._raw = obj

    def __repr__(self):
        return "<PWObject id={self.id}, type={self.type!r}, media_class={self.media_class!r}, name={self.name!r}>".format(self=self)

    @cached_property
    def id(self):
        return self._raw["id"]

    @cached_property
    def type(self):
        return self._raw.get("type", "").removeprefix("PipeWire:Interface:")

    @cached_property
    def info(self):
        return self._raw.get("info", {})

    @cached_property
    def direction(self):
        # input
        # output
        return self.info.get("direction", "")

    @cached_property
    def props(self):
        return self.info.get("props", {})

    @cached_property
    def port_direction(self):
        # in
        # out
        return self.props.get("port.direction", "")

    @cached_property
    def node_description(self):
        return self.props.get("node.description", "")

    @cached_property
    def node_name(self):
        return self.props.get("node.name", "")

    @cached_property
    def node_nick(self):
        return self.props.get("node.nick", "")

    @cached_property
    def device_id(self):
        return self.props.get("device.id", "")

    @cached_property
    def device_description(self):
        return self.props.get("device.description", "")

    @cached_property
    def device_nick(self):
        return self.props.get("device.nick", "")

    @cached_property
    def device_string(self):
        return self.props.get("device.string", "")

    @cached_property
    def device_bus(self):
        # bluetooth
        # pci
        # usb
        return self.props.get("device.bus", "")

    @cached_property
    def device_api(self):
        # alsa
        # bluez5
        # libcamera
        # v4l2
        return self.props.get("device.api", "")

    @cached_property
    def device_form_factor(self):
        # internal
        # microphone
        # headphone
        # webcam
        # ...
        return self.props.get("device.form-factor", "")

    @cached_property
    def device_icon_name(self):
        return self.props.get("device.icon-name", "")

    @cached_property
    def card_profile_device(self):
        # Used to find the correct route.
        return self.props.get("card.profile.device", "")

    @cached_property
    def alsa_id(self):
        # ALC221 Analog
        # USB Audio
        # HDMI 0
        # HDMI 1
        return self.props.get("alsa.id", "")

    @cached_property
    def node_id(self):
        return self.props.get("device.id", "")

    @cached_property
    def media_class(self):
        # Available in Nodes.
        return self.props.get("media.class", "")

    @cached_property
    def format_dsp(self):
        # Available in Ports.
        return self.props.get("format.dsp", "")

    @cached_property
    def is_sink(self):
        # Audio/Sink
        # Stream/Input/Audio
        return (
            False
            or "Sink" in self.media_class
            or "Input" in self.media_class
        )

    @cached_property
    def is_source(self):
        # Audio/Source
        # Audio/Source/Virtual
        # Stream/Output/Audio
        # Video/Source
        return (
            False
            or "Source" in self.media_class
            or "Output" in self.media_class
        )

    @cached_property
    def is_audio(self):
        # Audio/Device
        # Audio/Sink
        # Audio/Source
        # Audio/Source/Virtual
        return (
            False
            or "Audio" in self.media_class
            or "audio" in self.format_dsp
        )

    @cached_property
    def is_video(self):
        # Video/Device
        # Video/Source
        return "Video" in self.media_class

    @cached_property
    def is_midi(self):
        # Midi/Bridge
        return (
            False
            or "Midi" in self.media_class
            or "midi" in self.format_dsp
        )

    @cached_property
    def media_name(self):
        return self.props.get("media.name", "")

    @cached_property
    def device_profile_description(self):
        return self.props.get("device.profile.description", "")

    @cached_property
    def device_profile_name(self):
        return self.props.get("device.profile.name", "")

    @cached_property
    def port_alias(self):
        return self.props.get("port.alias", "")

    @cached_property
    def port_name(self):
        return self.props.get("port.name", "")

    @cached_property
    def name(self):
        if False:
            # Just for debugging.
            pprint({
                k: getattr(self, k)
                for k in [
                    "device_description",
                    "device_nick",
                    "device_profile_description",
                    "device_profile_name",
                    "media_name",
                    "node_description",
                    "node_name",
                    "node_nick",
                    "port_alias",
                    "port_name",
                ]
            })
        return (
            None
            # or self.node_nick  # ← This isn't helpful, as my both HDMI outputs have the same nick
            or self.device_nick
            or self.device_description
            or self.device_profile_description
            or self.node_description
            or self.media_name
            or self.device_profile_name
            or self.node_name
            or self.port_alias
            or self.port_name
        )

    @cached_property
    def params(self):
        return self.info.get("params", {})

    @cached_property
    def PropInfo(self):
        return self.params.get("PropInfo", [])

    @cached_property
    def Props(self):
        return self.params.get("Props", [])

    @cached_property
    def EnumFormat(self):
        return self.params.get("EnumFormat", [])

    @cached_property
    def Format(self):
        return self.params.get("Format", [])

    @cached_property
    def EnumPortConfig(self):
        return self.params.get("EnumPortConfig", [])

    @cached_property
    def PortConfig(self):
        return self.params.get("PortConfig", [])

    @cached_property
    def Latency(self):
        return self.params.get("Latency", [])

    @cached_property
    def ProcessLatency(self):
        return self.params.get("ProcessLatency", [])

    @cached_property
    def Tag(self):
        return self.params.get("Tag", [])

    @cached_property
    def EnumProfile(self):
        return self.params.get("EnumProfile", [])

    @cached_property
    def Profile(self):
        return self.params.get("Profile", [])

    @cached_property
    def EnumRoute(self):
        return self.params.get("EnumRoute", [])

    @cached_property
    def Route(self):
        return self.params.get("Route", [])

    @cached_property
    def Buffers(self):
        return self.params.get("Buffers", [])

    @cached_property
    def IO(self):
        return self.params.get("IO", [])

    @cached_property
    def Meta(self):
        return self.params.get("Meta", [])


class _PWFilter:
    def __init__(self, attr, values):
        self.attr = attr
        self.set_values = {}
        self.list_values = []
        if isinstance(values, (bytes, float, abc.Mapping, abc.MutableMapping)):
            raise TypeError("Unsupported type {} for filter {}={!r}".format(type(values), attr, values))
        elif isinstance(values, (bool, int, str, types.NoneType)):
            self.set_values = { values }
        elif isinstance(values, (abc.Set, abc.MutableSet)):
            self.set_values = values
        elif isinstance(values, (re.Pattern, types.FunctionType, types.LambdaType)):
            self.list_values = [ values ]
        elif isinstance(values, (abc.Sequence, abc.MutableSequence)):
            self.list_values = values
        else:
            raise TypeError("Unsupported type {} for filter {}={!r}".format(type(values), attr, values))

    def __repr__(self):
        return "<_PWFilter attr={} set={} list={}>".format(self.attr, self.set_values, self.list_values)

    def match(self, obj):
        # This will throw an exception if the attribute is not found.
        # This is by design.
        value = getattr(obj, self.attr)

        # Quick and easy O(1) checks:
        if value in self.set_values:
            return True

        # Slower filters:
        for item in self.list_values:
            if isinstance(item, (bool, int, str, types.NoneType, list)):
                if value == item:
                    return True
            elif isinstance(item, re.Pattern):
                if item.match(value):
                    return True
            elif isinstance(item, (types.FunctionType, types.LambdaType)):
                if item(value):
                    return True

        return False


class PWState:
    def __init__(self):
        self.db = {}
        self.lock = RLock()

    def __repr__(self):
        return "<PWState size={}>".format(len(self.db))

    def update(self, data):
        """Update its own internal state, based on the data.

        The data must be coming from a PWDump object.
        """
        with self.lock:
            # It's either a "RESET" string...
            if data == "RESET":
                self.db = {}
            else:
                # Or a list of PipeWire objects.
                for obj in data:
                    id = obj["id"]
                    if obj.get("info", {}) is None:
                        if id in self.db:
                            del self.db[id]
                        else:
                            # We won't delete an entry that we don't have.
                            # I don't even understand why this case happens,
                            # but it does happen. Very often.
                            pass
                    else:
                        self.db[id] = PWObject(obj)

    def get_by_ids(self, *ids):
        with self.lock:
            for id in ids:
                if id in self.db:
                    yield self.db[id]

    def get_by_id(self, id):
        """Returns the single object with that id.
        """
        for obj in self.get_by_ids(id):
            return obj
        return None

    def query_all(self, **filters):
        """Flexible powerful filtering method.

        TODO: write doctests. Well, there are a lot of tests that need to be written anyway.
        """
        filter_list = [ _PWFilter(attr, values) for (attr, values) in filters.items() ]
        with self.lock:
            for obj in self.db.values():
                if all(f.match(obj) for f in filter_list):
                    yield obj

    def query(self, **filters):
        """Returns the first object to match the filters, or None if not found.

        Hopefully it's the only object that matches it.
        """
        for obj in self.query_all(**filters):
            return obj
        return None


class PWQueryResult:
    def __init__(self, state, objs):
        self.state = state
        self.iterator = iter(objs)  # A list or a generator.

    def get(self):
        # Returns one single object.
        return next(self.iterator)

    def set_volume(self, *args, **kwargs):
        # Applies the volume to all objects.
        for obj in self.iterator:
            set_volume_absolute(self.state, obj.id, *args, **kwargs)

# TODO:
# * Write a get_volume
# * Write a set_volume_relative. It should also have a limit parameter to clamp to 100%.

def set_volume_absolute(state:PWState, id:int, volume:float|list|dict=None, *, mute:bool=None):
    if volume is None and mute is None:
        raise ValueError("At least one of `volume` and `mute` must be passed.")

    obj = state.get_by_id(id)
    if obj is None:
        raise ValueError("The id={} is invalid or not found.".format(id))
    if obj.type != "Node":
        raise ValueError("Pipewire object id={} has the wrong type, expected 'Node' but got {}.".format(id, obj.type))

    old_props = None
    for p in obj.Props:
        if all(x in p for x in ["channelVolumes", "mute"]):
            old_props = p
            break
    else:
        # Warning! Props not found!
        pass

    # For certain kinds of nodes/objects, we have to navigate to the route of the device.
    dev_id = obj.device_id
    dev_obj = None
    if dev_id:
        dev_obj = state.get_by_id(dev_id)
        if dev_obj is None:
            raise ValueError("The device.id={} from the object id={} is invalid or not found.".format(dev_id, id))
        for route in dev_obj.Route:
            if all(x in route for x in ["info", "props", "device", "index"]) and route["device"] == obj.card_profile_device:
                route_index = route["index"]
                route_device = route["device"]
                route_props = route["props"]
                old_props = route_props
                break
        else:
            raise RuntimeError("Could not find the route for node {} device {}".format(id, device_id))

    # old_props should be valid now.
    # Either coming from the Node object, or from the Device object.
    if not old_props:
        raise RuntimeError("Could not find the Props object. obj={} dev_obj={}".format(obj, dev_obj))
    new_props = {}

    if mute is not None:
        new_props["mute"] = mute

    if isinstance(volume, float):
        # Single number.
        # We replicate the number multiple times, repeating it for each channel.
        vol = volume_from_linear(volume)
        new_props["channelVolumes"] = [vol for i in old_props["channelVolumes"]]
    elif isinstance(volume, list):
        # List of numbers.
        # We assume the list has the same amount of numbers as the amount of channels.
        if len(volume) != len(old_props["channelVolumes"]):
            raise ValueError("Volume (as list) for this object expected exactly {} elements, but {} were passed.".format(len(old_props["channelVolumes"]), len(volume)))
        new_props["channelVolumes"] = [volume_from_linear(vol) for vol in volume]
    elif isinstance(volume, dict):
        # Dict of strings to numbers.
        # Specific channels from the dict will have the volume changed.
        # Any channel not listed in the dict will retain the previous volume.
        new_props["channelVolumes"] = [
            volume_from_linear(volume[ch_name]) if ch_name in volume else old_props["channelVolumes"][i]
            for (i, ch_name) in enumerate(route["channelMap"])
        ]

    if dev_id:
        # device_id?
        # Then we are setting the volume of hardware audio sources/sinks. (Or virtual ones.)
        # We can't set the volume of the device itself, because a single device
        # can have multiple routes, mapped to multiple Node objects.
        # (e.g. `HDA Intel PCH` can have routes to analog 3.5mm input/output jack, and also to the HDMI ports.)
        new_value = {
            "index": route_index,
            "device": route_device,
            "props": new_props,
            "save": True,
        }
        pprint(new_value)
        subprocess.run(
            ["pw-cli", "set-param", str(dev_id), "Route", json.dumps(new_value)],
            stdout=subprocess.DEVNULL,
        )
    else:
        # No device_id?
        # Then we are setting the volume of applications (Stream/Input/Audio and Stream/Output/Audio).
        # pprint(new_props)
        subprocess.run(
            ["pw-cli", "set-param", str(id), "Props", json.dumps(new_props)],
            stdout=subprocess.DEVNULL,
        )
