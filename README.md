## blight

A basic backlight utility using the logind SetBrightness method.

Use '-d/--device' to select the target device. Otherwise picks a default.
Use '+/-' to indicate relative changes and '%' to indicate fractional values.

Set values:
```
$ blight set 300 # absolute 300
$ blight set 50% # 50% of max
$ blight set +5% # +5% of max
$ blight set -- -10% # -10% of max
$ blight set 100% # max brightness
$ blight set 0 # off
```

See the manpage for more value formats.

Get values:
```
$ blight get default-device
backlight/intel_backlight
$ blight -d leds/dell::kbd_backlight get max-brightness
2
```

Toggle a led:
```
$ blight -d leds/dell::kbd_backlight toggle
```
