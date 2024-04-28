# midi-pipewire-volume 🎚🎛️ → 🔈🔉🔊

Tool to map MIDI CC (Control Change) messages to the audio volume of individual PipeWire nodes and devices.

Current status: early development, not ready for use.

Goals:

* Use MIDI CC messages to change individual volume levels in PipeWire.
    * Should support any device/node/port/whatever-it-is-called.
    * Should also support applications (because, why not?).
    * Should support individula channels (e.g. separate controls for left/right channels).
* Also use them to change the display brightness.
    * Using `ddcutil` for external displays.
    * Maybe someday using the backlight settings of laptops.
* Also allow changing the default audio device (both for playback and for recording).
* Also allow changing the profile of an audio device.
* Also allow arbitrary commands.
* Any MIDI message should work. CC messages are the most obvious, but note on/off could also be implemented.

## TODO

* [ ] Write a better README file.
    * Explain what this tool does, what it does not, and what are the alternative tools.
    * Step-by-step installation instructions.
    * Some configuration examples.
    * Video showing a live recording of this tool working.
* [x] Write a nice `set_volume` function that...
    * Accepts absolute amounts.
    * ~~Uses percent values (i.e. from 0 to 100), because adding `1` is easier and more precise than adding `0.01`~~.
    * Allows setting `mute`.
    * Allows per-channel changes.
* [ ] Write a nice `change_volume` function that...
    * Accepts relative amounts.
    * Has a maximum limit for relative amounts.
    * ~~Uses percent values (i.e. from 0 to 100), because adding `1` is easier and more precise than adding `0.01`.~~
    * Allows toggling `mute`.
    * Allows per-channel changes.
* [x] Hard-code changing the volume from a MIDI CC event.
* [ ] Write a nice function to change the default input/output device.
* [ ] Write a nice function to change the profile of a device.
* [ ] Allow changing the volume/mute of the default device.
* [ ] Let the user (i.e. the config file) decide if a MIDI device should be auto-connected to this tool.
* [ ] Auto-connect MIDI devices when they get hot-plugged.
* [ ] Send values back to the MIDI device
    * [ ] Send volume changes. (Requires figuring out how to detect volume changes.)
    * [ ] Send brightness/contrast VDU changes. (Requires receiving signals from ddcutil-session, not sure if it is possible.
    * [ ] Buy or borrow a MIDI device that I can test. Maybe I should just connect to my Akai Play Mini and map it to one of the knobs.
* [ ] Write some wrapper code to auto-reconnect to D-Bus when needed. (`sd_bus_internals.SdBusUnmappedMessageError` exception)
* [ ] Allow changing the backlight. Can be tricky, as I don't have a laptop to test it on.
    * [ ] Change the laptop backlight.
    * [ ] Change the keyboard backlight.
    * [ ] Maybe just a convenience function to write to an arbitrary file. That would allow changing the LED color of a connected PS4 controller.
* [ ] Write a lot of docstrings. Documentation is important.
* [ ] Write a lot of unit tests, possibly as doctests.
* [ ] Apply a Python linter/formatter such as Black or Ruff.
* [x] Figure out a nice configuration format. Or maybe just a simple API so that users can write their own code.
* [x] Write a function to send updates to `ddcutil-service`.
* [ ] Write a help function. Well, just use `argparse`. But write a parameter that prints out:
    * All the currently available MIDI devices/ports.
    * All the audio devices/nodes/etc.
    * Any significant changes detected.
    * Incoming MIDI messages.
    * Heck, this is just a `--verbose` mode!
* [ ] Write a `--dry-run` parameter, that won't change the volume or the brightness.

## Further links

* [PipeWire](https://pipewire.org/)
    * [How to change the volume in PipeWire](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Migrate-PulseAudio#sinksource-port-volumemuteport-latency) (TL;DR: it's complicated)
    * [Desire for official PipeWire Python bindings](https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/1654)
* [WirePlumber](https://pipewire.pages.freedesktop.org/wireplumber/)
    * [Getting a list of devices and applications, using `pw-dump` and `jq`](https://github.com/PipeWire/wireplumber/blob/0.5.1/src/tools/shell-completion/wpctl.zsh#L8-L20)
    * [Keyboard volume control using `wpctl`](https://wiki.archlinux.org/title/WirePlumber#Keyboard_volume_control)
    * [The source code of `wpctl set-volume`](https://github.com/PipeWire/wireplumber/blob/master/modules/module-mixer-api.c)
* Potentially related projects:
    * [deej](https://github.com/omriharel/deej) - Open-source hardware volume mixer. Requires custom hardware recognized as a serial interface, and a custom daemon written in Go. It's almost the same objective as this/my project, but my project aims to work with already existing MIDI devices.
    * [midi2input](https://gitlab.com/enetheru/midi2input) - Uses Lua and C++ to convert MIDI to arbitrary commands. Looks very versatile and more powerful than my project, but also more complicated.
    * [AV-MidiMacros](https://github.com/Avante-Vangard/AV-MidiMacros) - Shell script and a bunch of CSV files. Might be useful to someone.
    * [Translating MIDI input into computer keystrokes on Linux?](https://superuser.com/questions/1170136/translating-midi-input-into-computer-keystrokes-on-linux) - Has an ad-hoc solution using `aseqdump` and `xdotool`.
    * [Regulate system volume with midi controller](https://unix.stackexchange.com/questions/297449/regulate-system-volume-with-midi-controller)
