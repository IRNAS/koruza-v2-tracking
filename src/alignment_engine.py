import time
import logging
import xmlrpc.client

from threading import Thread, Lock

from ...src.constants import KORUZA_MAIN_PORT

"""
Alignment Engine used to expose easily readable methods to the end user.
Uses XMLRPC to communicate with main KORUZA code.
Exposes the following methods:
* move_motor - moves motor to specified position
* read_motor_position - get motor position
* read_sfp_data - get sfp data
* get_picture - get picture from camera
"""

class Unit():
    PRIMARY = "primary"
    SECONDARY = "secondary"

class AlignmentEngine():
    def __init__(self):
        """Initialize alignment engine"""
        self._koruza_proxy = None
    
    def initialize(self):
        """Return handles to primary and secondary unit"""
        self._koruza_proxy = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)
        return Unit.PRIMARY, Unit.SECONDARY

    def move_motor(self, unit, x, y):
        """Move motor on selected unit to position x and y"""
        if unit == Unit.SECONDARY:
            self._koruza_proxy.issue_remote_command("move_motors_to", (x, y))
        else:
            self._koruza_proxy.move_motors_to(x, y)

    def read_motor_position(self, unit):
        """Read motor position of specified unit"""
        if unit == Unit.SECONDARY:
            ret = self._koruza_proxy.issue_remote_command("get_motors_position", ())
            if ret is not None:
                x, y = ret
            else:
                x, y = None, None
        else:
            x, y = self._koruza_proxy.get_motors_position()

        return x, y

    def read_sfp_data(self, unit):
        """Read sfp data from specified unit"""
        if unit == Unit.SECONDARY:
            sfp_data = self._koruza_proxy.issue_remote_command("get_sfp_diagnostics", ())
        else:
            sfp_data = self._koruza_proxy.get_sfp_diagnostics()

        return sfp_data

    def get_picture(self, unit):
        """Return picture as int array"""
        if unit == Unit.SECONDARY:
            picture = self._koruza_proxy.issue_remote_command("take_picture", ())
        else:
            picture = self._koruza_proxy.take_picture()

        # print(f"Received picture: {picture}")
        return picture

    def get_calibration(self, unit):
        """Get calibration data of specified unit - useful when aligning calibrated cross to other unit's camera"""
        if unit == Unit.SECONDARY:
            calibration = self._koruza_proxy.issue_remote_command("get_calibration", ())
        else:
            calibration = self._koruza_proxy.get_calibration()

        return calibration

    def set_zoom_level(self, unit, zoom_level):
        """Change zoom level on specified unit"""
        if unit == Unit.SECONDARY:
            marker_x, marker_y = self._koruza_proxy.issue_remote_command("set_zoom_level", (zoom_level, ))
        else:
            marker_x, marker_y = self._koruza_proxy.set_zoom_level(zoom_level)

        return marker_x, marker_y