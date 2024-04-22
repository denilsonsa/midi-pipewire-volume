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
        pass
        # Display brightness change:
        #ddc.set_brightness_contrast([1, 2], brightness=message.value / 127)
    elif message.is_cc(6):
        pass
        # Display contrast change:
        #ddc.set_brightness_contrast([1, 2], contrast=message.value / 127)
    elif message.is_cc(7):
        # Display combined brightness-contrast change.
        # Works well for my AOC Q27P1 displays, but probably won't work well for other displays.
        # Please remember to check if you can see all the shades in a test image like this:
        # http://www.lagom.nl/lcd-test/contrast.php
        v = message.value
        LIMIT = 32  # out of 0~127 range
        ddc.set_brightness_contrast(
            displays=[1, 2],
            # From 0..LIMIT, brightness is 0.
            # From LIMIT..127, brightness is linearly scaled from 0% to 100%.
            brightness=max(0.00, 1.00 * (v - LIMIT) / (127 - LIMIT)),
            # From 0..LIMIT, contrast is linearly scaled from 0% to 50%.
            # From LIMIT..127, contrast is 50.
            contrast=min(0.50, 0.50 * v / LIMIT),
        )
