#!/bin/python

import usb.core
import usb.util
import glob
import serial

from zaber.serial import AsciiDevice, AsciiSerial
from os.path import realpath
from time import sleep

class StageController():
    def __init__(self, serial_port = None, devnum = 1, timeout = 30):
        self.port_is_open = False

        if serial_port is None:
            serial_port = self.get_usb_port()

        print("Opening Zaber device %d on %s " % (devnum, serial_port))
        self.port = AsciiSerial(serial_port, baud = 115200, timeout = timeout)
        self.port_is_open = True
        self.port.flush()

        self.dev = AsciiDevice(self.port, devnum)
        self.setup()

    def __del__(self):
        print("Closing serial port.")
        if self.port_is_open:
            self.port.close()

    def __getattr__(self,func_name):

        def handler(*args):
            return self.call_func(func_name, *args)

        return handler

    def setup(self):
        self.send("system reset")
        self.send("renumber")
        self.send("set system.led.enable 0")
        self.home()

    def call_func(self, func_name, *args):
        func = getattr(self.dev, func_name)
        return func(*args) 

    @staticmethod
    def get_usb_port(idVendor = 0x0403, idProduct = 0x6001):
        usbdev = usb.core.find(idVendor = idVendor, idProduct = idProduct)
        if usbdev is None:
            print("No device found!")
            raise Exception

        manu = usb.util.get_string(usbdev, usbdev.iManufacturer)
        prod = usb.util.get_string(usbdev, usbdev.iProduct)
        snum = usb.util.get_string(usbdev, usbdev.iSerialNumber)
        vals = [v.strip() for v in [manu, prod, snum] if v is not None]
        vals = [v.replace(" ", "_") for v in vals]
        identifier = "_".join(vals)
        devname = glob.glob("/dev/serial/by-id/usb-" + identifier + "*")

        if len(devname) != 1:
            print(str(len(devname)) + " devices found!")
            raise Exception

        return realpath(devname[0])

    @staticmethod
    def deg_to_ustep(deg):
        return round(deg * 4266.667)

    @staticmethod
    def mm_to_ustep(mm):
        return round(mm * 20997.38)

if __name__ == "__main__":
    controller = StageController()
