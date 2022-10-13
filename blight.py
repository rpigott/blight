#!/usr/bin/python3

import sys
import gi
gi.require_version("GUdev", "1.0")
from gi.repository import GUdev, GLib, Gio

import argparse
from functools import partial
import re

from math import floor, ceil, log, exp
from bisect import bisect_right as bisect, bisect_left
from operator import neg

def die(message):
	print(message, file = sys.stderr)
	exit(1)

def get_default_device():
	gclient = GUdev.Client()
	devices = gclient.query_by_subsystem("backlight")
	devices = [ (dev.get_sysfs_attr("type"), dev) for dev in devices ]

	# Prefer firmware
	for devtype, dev in devices:
		if devtype == "firmware":
			return dev

	# ... then platform
	for devtype, dev in devices:
		if devtype == "platform":
			return dev

	# ... then raw under enabled drm-connectors
	for devtype, dev in devices:
		if devtype == "raw":
			parent = dev.get_parent()
			enabled = parent.get_sysfs_attr("enabled")
			if enabled == "enabled":
				return dev
	
	die(f"Cannot find a suitable backlight device")

def get_named_device(devname):
	if '/' in devname:
		try:
			subsystem, name = devname.split('/')
		except ValueError as e:
			print(f"Invalid device name: {devname!r}")
			exit(1)
	else:
		subsystem = 'backlight'
		name = devname

	gclient = GUdev.Client()
	dev = gclient.query_by_subsystem_and_name(subsystem, name)
	if dev:
		return dev
	else:
		die(f"No such device: {devname!r}")

def devname(dev):
	subsystem = dev.get_subsystem()
	name = dev.get_name()
	return f"{subsystem}/{name}"

def logsteps(maxb, steps):
    steps = min(maxb - 1, steps)
    ret = list(range(1, steps + 1)) + [maxb]
    for n in range(1, steps):
        scale = (maxb / n) ** (1 / (steps - n + 1))
        sep = n * (scale - 1)
        if sep > 1: break
    for maxb in range(n, steps):
        ret[maxb] = ret[maxb - 1] * scale
    return list(map(round, ret))


def make_brightness_param(brightness, dev):
	return GLib.Variant(
		'(ssu)',
		[
			dev.get_subsystem(),
			dev.get_name(),
			round(brightness),
		]
	)

def parse_set_value(target, dev):
	max_brightness = dev.get_sysfs_attr_as_int("max_brightness")
	cur_brightness = dev.get_sysfs_attr_as_int("brightness")
	percent = max_brightness / 100

	if max_brightness < 99 and dev.get_sysfs_attr("type") == "raw":
		min_brightness = 0
	elif dev.get_subsystem() != "backlight":
		min_brightness = 0
	else:
		min_brightness = 1

	def clamp(brightness):
		if brightness < min_brightness:
			return min_brightness
		if brightness > max_brightness:
			return max_brightness
		return brightness

	# Log step
	if target.startswith('+//') or target.startswith('-//'):
		steps = int(target[0] + target[3:])
		if steps < 0:
			levels = logsteps(max_brightness, -steps)
			level = bisect_left(levels, cur_brightness)
			brightness = levels[max(0, level - 1)]
		else:
			levels = logsteps(max_brightness, steps)
			level = bisect(levels, cur_brightness)
			brightness = levels[min(steps, level)]

		return clamp(brightness)

	# Linear step
	if target.startswith('+/') or target.startswith('-/'):
		try:
			steps = max_brightness // int(target[0] + target[2:])
		except ValueError as e:
			die(f"Invalid brightness value: {target!r}")

		if not cur_brightness % steps:
			brightness = cur_brightness + steps
		else:
			brightness = cur_brightness - (cur_brightness % -steps)

		return clamp(brightness)

	# Relative set
	if target.startswith('x'):
		try:
			scale = float(target[1:])
		except ValueError as e:
			die(f"Invalid brightness value: {target!r}")

		brightness = round(cur_brightness * scale)
		if brightness == cur_brightness:
			if scale > 1:
				brightness += 1
			elif scale < 1:
				brightness -= 1

		return clamp(brightness)

	if target.startswith('/'):
		try:
			scale = float(target[1:])
		except ValueError as e:
			die(f"Invalid brightness value: {target!r}")

		brightness = round(cur_brightness / scale)
		if brightness == cur_brightness:
			if scale > 1:
				brightness -= 1
			elif scale < 1:
				brightness += 1

		return clamp(brightness)

	brightness = 0
	if target.startswith('+') or target.startswith('-'):
		brightness = cur_brightness

	# Absolute set
	value = 0
	try:
		if target.endswith('%'):
			value += float(target[:-1]) * percent
		else:
			value += float(target)
	except ValueError as e:
		die(f"Invalid brightness value: {target!r}")
	
	if value == 0:
		return brightness
	else:
		return clamp(brightness + value)

def set_brightness(target, dev = None):
	if not dev:
		dev = get_default_device()

	brightness = parse_set_value(target, dev)
	param = make_brightness_param(brightness, dev)
	logind_set_brightness(param)

def logind_set_brightness(param):
	method = [
		'org.freedesktop.login1',
		'/org/freedesktop/login1/session/self',
		'org.freedesktop.login1.Session',
		'SetBrightness'
	]

	bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
	try:
		bus.call_sync(
			*method, param, None,
			Gio.DBusCallFlags.NONE, -1, None
		)
	except GLib.GError as e:
		print(e.message, file = sys.stderr)

def parse_toggle_value(target, dev):
	max_brightness = dev.get_sysfs_attr_as_int("max_brightness")
	cur_brightness = dev.get_sysfs_attr_as_int("brightness")

	if not target:
		brightness = (cur_brightness + 1) % (max_brightness + 1)
		return brightness
	else:
		try:
			value = int(target)
		except ValueError as e:
			die(f"Invalid toggle value")

	brightness = 0
	if target.startswith('+') or target.startswith('-'):
		brightness = (cur_brightness + value) % (max_brightness + 1)
	elif not cur_brightness == value:
		brightness = value
	return brightness

def toggle_leds(target, dev = None):
	if not dev:
		dev = get_default_device()

	brightness = parse_toggle_value(target, dev)
	param = make_brightness_param(brightness, dev)
	logind_set_brightness(param)

getters = {
	'default-device': None, # Handled
	'brightness': lambda dev: dev.get_sysfs_attr("brightness"),
	'max-brightness': lambda dev: dev.get_sysfs_attr("max_brightness"),
}

def get_value(value, dev = None):
	if value == "default-device":
		dev = get_default_device()
		return devname(dev)

	if value == "help":
		return list(getters)

	if not dev:
		dev = get_default_device()

	if value in getters:
		return getters[value](dev)
	elif not value:
		return getters["brightness"](dev)
	else:
		die(f"Unknown query: {value!r}")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog = "blight")
	parser.add_argument('-d', '--device', help = "Which backlight device to modify")

	subparsers = parser.add_subparsers(dest = "action", required = True)

	parser_set = subparsers.add_parser("set", help = "Set an exact or relative brightness value")
	parser_set.add_argument("value", help = "A brightness value.")

	parser_get = subparsers.add_parser("get", help = "Inspect brightness devices")
	parser_get.add_argument("value", help = "Value to get", nargs = '?')

	parser_toggle = subparsers.add_parser("toggle", help = "Toggle a led")
	parser_toggle.add_argument("value", help = "Value to toggle when on", nargs = '?')

	# replace '-' for numbers
	escape = partial(re.sub, r'^-(?=[0-9/])', '\u2212')
	argv = list(map(escape, sys.argv[1:]))
	args = parser.parse_args(argv)
	dev = get_named_device(args.device) if args.device else None

	if args.action == "set":
		value = args.value.replace('\u2212', '-')
		set_brightness(value, dev = dev)
	elif args.action == "toggle":
		value = args.value and args.value.replace('\u2212', '-')
		toggle_leds(value, dev = dev)
	elif args.action == "get":
		result = get_value(args.value, dev = dev)
		if isinstance(result, list):
			for item in result:
				print(item)
		else:
			print(result)
