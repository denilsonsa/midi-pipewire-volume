# Custom user configuration.
# Should be located at ~/.config/midipwvol/midipwvolconfig.py


def handle_midi_message(port, message, pw, ddc):
    if message.is_cc(0):
        pw(type="Node", node_description="Built-in Audio Analog Stereo", is_audio=True, is_sink=True).set_volume(message.value / 127)
    elif message.is_cc(1):
        pw(type="Node", node_description="Built-in Audio Digital Stereo (HDMI)", is_audio=True, is_sink=True).set_volume(message.value / 127)
        #pw(type="Node", node_description="Built-in Audio Digital Stereo (HDMI 2)", is_audio=True, is_sink=True).set_volume(message.value / 127)
    elif message.is_cc(2):
        pw(type="Node", media_name="Aeropex by AfterShokz", is_audio=True, is_sink=True).set_volume(message.value / 127)
    elif message.is_cc(3):
        pw(type="Node", node_description={"Logitech USB Microphone Mono", }, is_audio=True, is_source=True).set_volume(message.value / 127)
    elif message.is_cc(4):
        pw(type="Node", media_name="Jellyfin", node_name="Firefox", is_audio=True, is_source=True).set_volume(message.value / 127)
    elif message.is_cc(5):
        ddc.set_brightness_contrast([1, 2], brightness=message.value * 100 / 127)
    elif message.is_cc(6):
        ddc.set_brightness_contrast([1, 2], contrast=message.value * 100 / 127)
