blight(1)

# NAME

blight - A desktop independent backlight utility

# SYNOPSIS

*blight* [options...] [command] [args]

# OPTIONS

*-h, --help*
	Show help message and quit.

*-d, --device* <device>
	Specify which device to act on. If not specified, chooses a sane
	default. Format is <subsystem>/<device>, e.g. "backlight/intel_backlight"

# COMMANDS

*set* <value>
	Set a brightness value. There are several accepted formats for _value_
	with different meanings. See the *VALUE FORMATS* section below.

*get* [value]
	Gets and prints a value. If no value is specified, get the brightness
	value for the device. _value_ may be:

	_default-device_ shows which device is acted on by default.

	_brightness_ shows the current brightness value in device units.

	_max-brightness_ shows the maximum brightness value in device units.

*toggle* [value]
	Toggle through the available brightness values. If an absolute value is
	provided, switch between that value and 0 (off). Otherwise, specify a
	relative value to change the order of the toggle values.

# VALUE FORMATS

The *set* command takes values in several formats that change it's behavior. For
any value but an Absolute Value, if the requested value would turn the backlight
completely off, the value is clamped to the active range of the device. If the
requested value is greater than _max-brightness_ it will also be clamped. Values
may be floating point.

*n* (Absolute Value)
	Set the absolute brightness to this value using the internal units of
	of the device. If value is greater than _max-brightness_, it will be
	clamped.

*n%* (Absolute Percentage)
	Set the brightness of the device to the given percent of the maximum
	brightness value.

*+n*, *-n* (Linear Relative Value)
	Add or subtract to the current brightness value in the internal units of
	the device. If the result is greater than _max-brightness_ it will be
	clamped.

*+n%*, *-n%* (Relative Percentage)
	Add or subtract to the current brightness value in units of percentage
	of the maximum brightness.

*xn*, */n* (Geometric Relative Value)
	Multiply or divide the current brightness value. Multiplying by a factor
	greater than one or dividing by a factor less than one is guaranteed to
	increase the brightness of the device by at least one unit if possible, 
	and similar for decreasing the brightness.

*+/n*, *-/n* (Stepped Linear Value)
	Step the brightness up or down to the next level in a set number of
	divisions of the maximum brightness. For example, '+/10' for a backlight
	of maximum brightness 100 would change brightness 11 to 20, and '-/10'
	from 11 to 10. '-/10' again from 10 would reduce to 1 if 0 would turn
	the backlight off. A value _n_ has exactly _n_ divisions, or _n_+1 levels,
	including the lowest level.

*+//n*, *-//n* (Stepped Geometric Value)
	Step the brightness up or down to the next level in a set number of
	logarithmic divisions of the maximum brightness. A value _n_ is
	guaranteed to have _n_+1 levels, separated by at least one device unit. 

# AUTHOR

Maintained by Ronan Pigott <rpigott@berkeley.edu>
