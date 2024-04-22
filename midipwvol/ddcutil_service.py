from threading import Timer

# pip install sdbus
# https://python-sdbus.readthedocs.io/en/latest/general.html
from sdbus import DbusInterfaceCommon, dbus_method, dbus_property
# If sdbus doesn't work well, maybe worth trying the alternatives listed at:
# https://gitlab.freedesktop.org/dbus/dbus-python/


def debounce(timeout):
    def decorator(func):
        existing_timer = None
        def decorated(*args, **kwargs):
            nonlocal existing_timer
            if existing_timer:
                existing_timer.cancel()
            existing_timer = Timer(timeout, func, args=args, kwargs=kwargs)
            existing_timer.start()
        return decorated
    return decorator


# See: https://github.com/digitaltrails/ddcutil-service/blob/master/ddcutil-service.c
class DdcutilInterface(DbusInterfaceCommon, interface_name="com.ddcutil.DdcutilInterface"):
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

    # TODO: How can I make this timeout configurable by the user?
    # Maybe by making it an explicit parameter and discarding the neat decorator.
    @debounce(0.25)
    def set_brightness_contrast(self, displays:list[int], brightness=None, contrast=None):
        actions = []
        if brightness is not None:
            actions.append((0x10, int(brightness)))
        if contrast is not None:
            actions.append((0x12, int(contrast)))

        for display in displays:
            for code, value in actions:
                self.SetVcp(display, "", code, value, 0)
