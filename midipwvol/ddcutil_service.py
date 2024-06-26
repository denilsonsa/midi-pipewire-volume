from collections import defaultdict
from dataclasses import dataclass
from threading import Lock, Timer

# pip install sdbus
# https://python-sdbus.readthedocs.io/en/latest/general.html
from sdbus import DbusInterfaceCommon, dbus_method, dbus_property
from sdbus import sd_bus_open, set_default_bus
from sdbus.exceptions import SdBusUnmappedMessageError
# If sdbus doesn't work well, maybe worth trying the alternatives listed at:
# https://gitlab.freedesktop.org/dbus/dbus-python/


@dataclass
class DisplayValues:
    brightness: int | None = None
    contrast: int | None = None


# See: https://github.com/digitaltrails/ddcutil-service/blob/master/ddcutil-service.c
class DdcutilInterface(DbusInterfaceCommon, interface_name="com.ddcutil.DdcutilInterface"):
    def __init__(self, *args, **kwargs):
        # Used for debouncing.
        # Calling ddcutil-service is slow, we should throttle/debounce the calls to it.
        self.timer_thread = None
        self.timer_lock = Lock()
        self.future_values = defaultdict(DisplayValues)

        super().__init__(*args, **kwargs)

    def _auto_reconnect(self):
        # This method is a hack.
        # It's using private attributes and may break on any sdbus update.
        try:
            self.dbus_ping()
            print("dbus_ping ok")
        except SdBusUnmappedMessageError:
            print("dbus_ping failed")
            new_bus = sd_bus_open()
            self._dbus.attached_bus = new_bus
            set_default_bus(new_bus)

    @dbus_method("u")
    def Detect(self, flags:int) -> tuple[int, list[tuple], int, str]:
        # Returns:
        # * number_of_displays (signed 32-bit integer)
        # * detected_displayes (array of a struct of many elements)
        # * error_status (signed 32-bit integer)
        # * error_message (string)
        raise NotImplementedError

    # TODO: Other methods, such as:
    # * GetVcp
    # * GetMultipleVcp
    # * SetVcpWithContext
    # * GetDisplayState (probably useless)
    # 
    # Possibly some properties, such as:
    # * DdcutilVersion
    # * ServiceInterfaceVersion
    # * AttributesReturnedByDetect
    # * ServiceEmitConnectivitySignals
    # * StatusValues
    #
    # TODO: Some signals, but they require the async interface (insted of the blocking interface):
    # * ConnectedDisplaysChanged
    # * VcpValueChanged signal

    @dbus_method("isyqu")
    def SetVcp(self, display:int, edid_txt:str, vcp_code:int, vcp_new_value:int, flags:int) -> tuple[int, str]:
        # Returns:
        # * error_status (signed 32-bit integer)
        # * error_message (string)
        raise NotImplementedError

    def set_brightness_contrast(self, displays:list[int], brightness:float=None, contrast:float=None, wait=0.25):
        # brightness/contrast are in the 0.0 to 1.0 range.
        # Schedules the display/brightness/contrast values to be updated by the timer thread.
        if self.timer_thread:
            self.timer_thread.cancel()
        with self.timer_lock:
            for display in displays:
                if brightness is not None:
                    self.future_values[display].brightness = brightness
                if contrast is not None:
                    self.future_values[display].contrast = contrast
        self.timer_thread = Timer(wait, self._set_brightness_contrast)
        self.timer_thread.start()

    def _set_brightness_contrast(self):
        # Runs in a Timer thread (after a short delay).
        actions = []

        with self.timer_lock:
            for display, values in list(self.future_values.items()):
                del self.future_values[display]
                if (v := values.brightness) is not None:
                    actions.append((display, 0x10, round(100 * v)))
                if (v := values.contrast) is not None:
                    actions.append((display, 0x12, round(100 * v)))

        print(repr(actions))
        self._auto_reconnect()
        for (display, code, value) in actions:
            self.SetVcp(display, "", code, value, 0)
