# -*- coding: utf-8 -*-
"""
    console.py - colored console output, menu & prompt helpers.
    Copyright (C) 2009-2010 Petr Morávek

    This file is part of Pyggs.

    Pyggs is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    Pyggs is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

__version__ = "0.3.1"
__all__ = ["ColorLogging", "prompt", "menu", "color"]


import logging
import platform
import re
import sys

if platform.system() == "Windows":
    from ctypes import windll


useColor = True

if platform.system() == "Windows":
    codes = {}
    codes["bold"] = 8
    codes["colors"] = {"R":4, "G":2, "B":1}

    def color(font="RGB", bold=False, background=""):
        color = 0
        for col in font:
            if col in codes["colors"]:
                color = color + codes["colors"][col]
        for col in background:
            if col in codes["colors"]:
                color = color + codes["colors"][col]*16
        if bold:
            color = color + codes["bold"]
        return color


    def changeColor(color, stream):
        if not useColor:
            return

        if stream == sys.stdout:
            hdl = windll.kernel32.GetStdHandle(-11)
        elif stream == sys.stderr:
            hdl = windll.kernel32.GetStdHandle(-12)
        else:
            return

        windll.kernel32.SetConsoleTextAttribute(hdl, color)
else:
    codes = {}
    codes["colors"] = {"R":1, "G":2, "B":4}

    def color(font=None, bold=False, background=None):
        color = "\x1b["

        if font is not None:
            fontColor = 30
            for col in font:
                if col in codes["colors"]:
                    fontColor = fontColor + codes["colors"][col]
            color = color + str(fontColor)

        if background is not None:
            backgroundColor = 40
            for col in background:
                if col in codes["colors"]:
                    backgroundColor = backgroundColor + codes["colors"][col]
            if color != "\x1b[":
                color = color + ";"
            color = color + str(backgroundColor)

        if bold:
            if color != "\x1b[":
                color = color + ";"
            color = color + "1"

        if color == "\x1b[":
            color = color + "0"

        color = color + "m"

        if not bold:
            color = "\x1b[0m" + color

        return color


    def changeColor(color, stream):
        if not useColor:
            return

        stream.write(color)
        flush(stream)


colors = {}
colors["reset"] = color("RGB", False, "")


def writeln(message, color, stream=sys.stdout):
    write(message, color, stream)
    stream.write("\n")
    flush(stream)


def write(message, color, stream=sys.stdout):
    changeColor(color, stream)
    stream.write(message)
    flush(stream)
    changeColor(colors["reset"], stream)


def flush(stream):
    if hasattr(stream, "flush"):
        stream.flush()


def prompt(question, padding=0, default=None, validate=None):
        message = "  "*int(padding)
        message = message + question
        if default is not None:
            message = message + " [{0}]".format(default)
        if isinstance(validate, list):
            message = message.format(CHOICES=", ".join(validate))
        write(message, color("RGB", True, ""))
        value = input(" ")
        if len(value) == 0 and default is not None:
            value = default

        error = None
        if isinstance(validate, list):
            if value not in validate:
                error = _("Please, input a value from {0}.").format(", ".join(validate))
        elif hasattr(validate, "__call__"):
            error = validate(value)
        elif validate == "BOOLEAN":
            if value.lower() in (_("y"), _("yes")):
                value = True
            elif value.lower() in (_("n"), _("no")):
                value = False
            else:
                error = _("Please, answer yes/no (y/n).")
        elif validate == "INTEGER":
            if value.isdigit():
                value = int(value)
            else:
                error = _("Use only digits, please.")
        elif validate == "DECIMAL":
            if re.match("^-?[0-9]+\.?[0-9]*$", value) is not None:
                value = float(value)
            else:
                error = _("Please, input a decimal number.")
        elif validate == "ALNUM":
            if not value.isalnum():
                error = _("Please, use only alpha-numeric characters.")
        elif validate is not None:
            if len(value) == 0:
                error = _("Please, input a non-empty string.")

        if error is not None:
            writeln("{0}{1}: {2}".format("  "*padding, _("ERROR"), error), color("R", False, ""))
            value = prompt(question, padding, default, validate)

        return value


def menuValidator(choices, value):
    if not (value in choices or (value.isdigit() and int(value) >= 1 and int(value) <= len(choices))):
        return _("Please, chose an option from the list - input a number, or a full text of the desired option.")


def menu(header, choices, padding=0, default=None):
    writeln("{0}{1}".format("  "*padding, header), color("RGB", True, ""))
    for i in range(len(choices)):
        print("{0}{1:2d}) {2}".format("  "*(padding+1), i+1, choices[i]))
    value = prompt(_("Select") + ":", padding+1, default, lambda val: menuValidator(choices, val))
    if value.isdigit() and int(value) >= 1 and int(value) <= len(choices):
        return choices[int(value)-1]
    else:
        return value



class ColorLogging(logging.StreamHandler):
    colors = {}
    colors["notset"] = color("GB", False, "")
    colors["debug"] = color("RB", False, "")
    colors["info"] = color("RGB", True, "")
    colors["warning"] = color("RG", True, "")
    colors["error"] = color("R", True, "")
    colors["critical"] = color("RG", True, "R")

    def __init__(self, useColor=True, fmt="%(levelname)-8s %(name)-15s %(message)s", datefmt=None, colors={}):
        self.colors.update(colors)
        logging.StreamHandler.__init__(self)
        useColor = useColor
        self.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))


    def getColor(self, record):
        if self.colors.get(record.levelname.lower()) is not None:
            return self.colors.get(record.levelname.lower())
        elif record.levelno >= 50:
            return self.colors["critical"]
        elif record.levelno >= 40:
            return self.colors["error"]
        elif record.levelno >= 30:
            return self.colors["warn"]
        elif record.levelno >= 20:
            return self.colors["info"]
        elif record.levelno >= 10:
            return self.colors["debug"]
        else:
            return self.colors["notset"]


    def emit(self, record):
        color = colors["reset"]
        if useColor:
            color = self.getColor(record)

        try:
            msg = self.format(record)
            writeln(str(msg), color, self.stream)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass

        if record.levelno >= 50:
            raise SystemExit(1)
