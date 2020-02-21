#!/usr/bin/python3

import sys
import gi
gi.require_version("GUdev", "1.0")
from gi.repository import GUdev, GLib, Gio

import argparse

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
	
	print(f"Cannot find a suitable backlight device", file = sys.stderr)
	exit(1)

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
		print(f"No such device: {devname!r}")
		exit(1)

def devname(dev):
	subsystem = dev.get_subsystem()
	name = dev.get_name()
	return f"{subsystem}/{name}"

def make_param(target, dev):
	max_brightness = dev.get_sysfs_attr_as_int("max_brightness")
	cur_brightness = dev.get_sysfs_attr_as_int("brightness")
	percent = max_brightness / 100

	if max_brightness < 99 and dev.get_sysfs_attr("type") == "raw":
		min_brightness = 0
	else:
		min_brightness = 1

	brightness = 0
	if target.startswith('-') or target.startswith('+'):
		brightness = cur_brightness

	try:
		if target.endswith('%'):
			brightness += float(target[:-1]) * percent
		else:
			brightness += float(target)
	except ValueError as e:
		print(f"Invalid brightness value: {target!r}", file = sys.stderr)
		exit(1)

	if brightness < min_brightness:
		brightness = min_brightness
	if brightness > max_brightness:
		brightness = max_brightness

	return GLib.Variant(
		'(ssu)',
		[
			dev.get_subsystem(),
			dev.get_name(),
			round(brightness),
		]
	)

def set_brightness(target, dev = None):
	if not dev:
		dev = get_default_device()

	method = [
		'org.freedesktop.login1',
		'/org/freedesktop/login1/session/self',
		'org.freedesktop.login1.Session',
		'SetBrightness'
	]

	param = make_param(target, dev)

	bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
	bus.call_sync(
		*method, param, None,
		Gio.DBusCallFlags.NONE, -1, None
	)


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
	else:
		print(f"Unknown query: {value!r}")
		exit(1)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog = "blight")
	parser.add_argument('-d', '--device', help = "Which backlight device to modify")

	subparsers = parser.add_subparsers(dest = "action", required = True)

	parser_set = subparsers.add_parser("set", help = "Set a value")
	parser_set.add_argument("value", help = "A brightness value.")

	parser_get = subparsers.add_parser("get", help = "Get a value")
	parser_get.add_argument("value", help = "Value to get")

	args = parser.parse_args()
	dev = get_named_device(args.device) if args.device else None

	if args.action == "set":
		set_brightness(args.value, dev = dev)
	elif args.action == "get":
		result = get_value(args.value, dev = dev)
		if isinstance(result, list):
			for item in result:
				print(item)
		else:
			print(result)

