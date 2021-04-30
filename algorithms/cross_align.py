import xmlrpc.client
import time
import logging
import random
from threading import Thread, Lock

from ..src.heatmap import Heatmap
from ..src.cross_scan import CrossScan

from ...src.constants import KORUZA_MAIN_PORT, DEVICE_MANAGEMENT_PORT

# NOTE THIS FUNCTIONS REALLY POORLY

# TODO read from file
offset_x_master = 282
offset_y_master = 528

offset_x_slave = 462
offset_y_slave = 292

heatmap_primary = Heatmap(offset_x_master, offset_y_master)
heatmap_secondary = Heatmap(offset_x_slave, offset_y_slave)

log = logging.getLogger()

class CrossAlign():
    def __init__(self, heatmap_primary, heatmap_secondary):
        """Init algorithm variables"""

        self.heatmap_primary = heatmap_primary
        self.heatmap_secondary = heatmap_secondary

        # keep track of maximum values in each iteration
        # one iteration is one spiral of either primary or secondary unit
        self.max_point_primary = {"x": 0, "y": 0, "dBm": -40}
        self.max_point_secondary = {"x": 0, "y": 0, "dBm": -40}

        self.client = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)  # client to koruza
        time.sleep(2)  # wait for client to init

        self.current_pos_x_primary = None
        self.current_pos_y_primary = None

        self.current_pos_x_secondary = None
        self.current_pos_y_secondary = None

        self.lock = Lock()

        self.cross_scan_primary = CrossScan(self.client, 0, 0, remote=False, lock=self.lock)
        self.cross_scan_secondary = CrossScan(self.client, 0, 0, remote=True, lock=self.lock)

        self.running = True

        self.monitor_thread = Thread(target=self.get_unit_diagnostics, daemon=True)
        self.monitor_thread.start()

    def __del__(self):
        """Destructor"""
        self.running = False
        self.monitor_thread.join()

    def get_unit_diagnostics(self):
        """Get both unit diagnostics in a short interval"""

        while self.running:
            self.lock.acquire()

            try:
                pos_x_secondary, pos_y_secondary = self.client.issue_remote_command("get_motors_position", ())
                rx_dBm_secondary = self.client.issue_remote_command("get_sfp_diagnostics", ())["sfp_0"]["diagnostics"]["rx_power_dBm"]

                pos_x_primary, pos_y_primary = self.client.get_motors_position()
                rx_dBm_primary = self.client.get_sfp_diagnostics()["sfp_0"]["diagnostics"]["rx_power_dBm"]

                if rx_dBm_secondary > self.max_point_secondary["dBm"]:
                    self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                    print(f"New max point on secondary unit: {self.max_point_secondary}")

                if rx_dBm_primary > self.max_point_primary["dBm"]:
                    # update both max points! - since max depends on both positions, not only one
                    self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                    print(f"New max point on primary unit: {self.max_point_primary}")

                # if rx_dBm_secondary > self.max_point_secondary["dBm"] or rx_dBm_primary > self.max_point_primary["dBm"]:

                #     # update max points if total dBm is higher than previously
                #     if rx_dBm_primary + rx_dBm_secondary > self.max_point_primary["dBm"] + self.max_point_secondary["dBm"]:
                #         self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                #         print(f"New max point on secondary unit: {self.max_point_secondary}")

                #         # update both max points! - since max depends on both positions, not only one
                #         self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                #         print(f"New max point on primary unit: {self.max_point_primary}")

                self.heatmap_primary.add_point(pos_x_primary, pos_y_primary, rx_dBm_primary)
                self.heatmap_secondary.add_point(pos_x_secondary, pos_y_secondary, rx_dBm_secondary)
                
            except Exception as e:
                log.error(f"Error getting rx_dBm: {e}")

            self.lock.release()

            time.sleep(0.2)

    def move_primary_to_primary_max(self):
        """Move to currently saved max position"""
        self.cross_scan_primary.move_to_position(self.max_point_primary["x"], self.max_point_primary["y"])

    def move_primary_to_secondary_max(self):
        """Move to currently saved max position"""
        self.cross_scan_primary.move_to_position(self.max_point_secondary["x"], self.max_point_secondary["y"])

    def move_secondary_to_primary_max(self):
        """Move to currently saved max position"""
        self.cross_scan_secondary.move_to_position(self.max_point_primary["x"], self.max_point_primary["y"])

    def move_secondary_to_secondary_max(self):
        """Move to currently saved max position"""
        self.cross_scan_secondary.move_to_position(self.max_point_secondary["x"], self.max_point_secondary["y"])

def align_primary_secondary():
    """Align so primary is aligned first and secondary later"""
    cross_align = CrossAlign(heatmap_primary, heatmap_secondary)

    # # 1. Start by moving to upper left corner, set wih max_offset
    # max_offset = 1500
    # vertical_step = 500
    # cross_align.lock.acquire()
    # cross_align.client.issue_remote_command("home", ())  # home secondary unit
    # cross_align.lock.release()
    # time.sleep(30)
    # cross_align.cross_scan_primary.scan_window(max_offset, vertical_step)

    # cross_align.lock.acquire()
    # cross_align.client.home()  # home primary unit
    # cross_align.lock.release()
    # time.sleep(30)
    # cross_align.cross_scan_secondary.scan_window(max_offset, vertical_step)

    cross_align.heatmap_primary.clear_heatmap()  # clear heatmap
    cross_align.heatmap_secondary.clear_heatmap()  # clear heatmap

    # move both to max position
    cross_align.move_primary_to_primary_max()  # move to position where other unit rx was highest
    cross_align.move_secondary_to_secondary_max()  # move to position where other unit rx was highest

    # repeat a few times
    prev_primary_max = None
    prev_secondary_max = None
    for i in range(0, 4):
        steps = [1000, 500, 300, 200, 100]

        for step in steps:
            # start doing crosses on main
            cross_align.cross_scan_primary.do_cross(step)
            cross_align.heatmap_primary.clear_heatmap()  # clear heatmap

            # start doing crosses on main
            cross_align.cross_scan_secondary.do_cross(step)
            cross_align.heatmap_secondary.clear_heatmap()  # clear heatmap

            cross_align.move_primary_to_primary_max()  # move to position where other unit rx was highest
            cross_align.move_secondary_to_secondary_max()  # move to position where other unit rx was highest


            if prev_primary_max == cross_align.max_point_primary:
                random_x = random.randrange(-500, 500, 250)
                random_y = random.randrange(-500, 500, 250)
                cross_align.cross_scan_primary.move_to_position(cross_align.current_pos_x_primary + random_x, cross_align.current_pos_x_primary + random_y)

            if prev_secondary_max == cross_align.max_point_secondary:
                random_x = random.randrange(-500, 500, 250)
                random_y = random.randrange(-500, 500, 250)
                cross_align.cross_scan_secondary.move_to_position(cross_align.current_pos_x_secondary + random_x, cross_align.current_pos_x_secondary + random_y)

            prev_primary_max = cross_align.max_point_primary
            prev_secondary_max = cross_align.max_point_secondary

align_primary_secondary()