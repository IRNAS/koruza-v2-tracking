import xmlrpc.client
import time
import logging
import random
from threading import Thread, Lock

from ..src.heatmap import Heatmap
from ..src.cross_scan import CrossScan
from ..src.spiral_scan import SpiralScan

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

        self.cross_scan_primary = CrossScan(self.client, remote=False, lock=self.lock)
        self.cross_scan_secondary = CrossScan(self.client, remote=True, lock=self.lock)

        self.spiral_scan_primary = SpiralScan(self.client, remote=False, lock=self.lock)
        self.spiral_scan_secondary = SpiralScan(self.client, remote=True, lock=self.lock)

        self.running = True

        self.monitor_thread = Thread(target=self.get_unit_diagnostics, daemon=True)
        self.monitor_thread.start()

    def __del__(self):
        """Destructor"""
        self.running = False
        self.monitor_thread.join()

    def get_unit_diagnostics(self):
        """Get both unit diagnostics in a short interval"""

        max_dBm = -100
        max_sum_dBm = -100

        while self.running:

            try:
                self.lock.acquire()
                pos_x_secondary, pos_y_secondary = self.client.issue_remote_command("get_motors_position", ())
                self.lock.release()

                self.lock.acquire()
                rx_dBm_secondary = self.client.issue_remote_command("get_sfp_diagnostics", ())["sfp_0"]["diagnostics"]["rx_power_dBm"]
                self.lock.release()


                self.lock.acquire()
                pos_x_primary, pos_y_primary = self.client.get_motors_position()
                self.lock.release()
                
                self.lock.acquire()
                rx_dBm_primary = self.client.get_sfp_diagnostics()["sfp_0"]["diagnostics"]["rx_power_dBm"]
                self.lock.release()

                # # STRATEGY 1 - update each individual maximum independently
                # if rx_dBm_secondary > self.max_point_secondary["dBm"]:
                #     self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                #     print(f"New max point on secondary unit: {self.max_point_secondary}")

                # if rx_dBm_primary > self.max_point_primary["dBm"]:
                #     # update both max points! - since max depends on both positions, not only one
                #     self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                #     print(f"New max point on primary unit: {self.max_point_primary}")

                # # STRATEGY 2 - update both maximum if sum is maximum
                # if rx_dBm_secondary > self.max_point_secondary["dBm"] or rx_dBm_primary > self.max_point_primary["dBm"]:

                #     # update max points if total dBm is higher than previously
                #     if rx_dBm_primary + rx_dBm_secondary > self.max_point_primary["dBm"] + self.max_point_secondary["dBm"]:
                #         self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                #         print(f"New max point on secondary unit: {self.max_point_secondary}")

                #         # update both max points! - since max depends on both positions, not only one
                #         self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                #         print(f"New max point on primary unit: {self.max_point_primary}")

                # # STRATEGY 3 - update both maximums if one of them is lowest
                # if rx_dBm_secondary > max_dBm or rx_dBm_primary > max_dBm:

                #     self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                #     print(f"New max point on secondary unit: {self.max_point_secondary}")

                #     # update both max points! - since max depends on both positions, not only one
                #     self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                #     print(f"New max point on primary unit: {self.max_point_primary}")

                #     max_dBm = rx_dBm_primary if rx_dBm_primary > rx_dBm_secondary else rx_dBm_secondary
                #     print(f"New total max dBm: {max_dBm}")

                # # STRATEGY 4 - update both maximums if one of them is lowest OR sum is lowest
                # if rx_dBm_secondary > max_dBm or rx_dBm_primary > max_dBm or rx_dBm_primary + rx_dBm_secondary > max_sum_dBm:

                #     self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                #     print(f"New max point on secondary unit: {self.max_point_secondary}")

                #     # update both max points! - since max depends on both positions, not only one
                #     self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                #     print(f"New max point on primary unit: {self.max_point_primary}")

                #     max_dBm = rx_dBm_primary if rx_dBm_primary > rx_dBm_secondary else rx_dBm_secondary
                #     print(f"New total max dBm: {max_dBm}")

                #     if rx_dBm_primary + rx_dBm_secondary > max_sum_dBm:
                #         max_sum_dBm = rx_dBm_primary + rx_dBm_secondary
                #         print(f"New total sum dBm: {max_sum_dBm}")

                self.heatmap_primary.add_point(pos_x_primary, pos_y_primary, rx_dBm_primary)
                self.heatmap_secondary.add_point(pos_x_secondary, pos_y_secondary, rx_dBm_secondary)

                
            except Exception as e:
                self.lock.release()
                log.error(f"Error getting rx_dBm: {e}")            

            time.sleep(0.2)

    def move_primary_to_max(self):
        """Move to currently saved max position"""
        self.cross_scan_primary.move_to_position(self.max_point_primary["x"], self.max_point_primary["y"])

    def move_secondary_to_max(self):
        """Move to currently saved max position"""
        self.cross_scan_secondary.move_to_position(self.max_point_secondary["x"], self.max_point_secondary["y"])

def align_primary_secondary():
    """Align so primary is aligned first and secondary later"""
    cross_align = CrossAlign(heatmap_primary, heatmap_secondary)

    # 1. Start by moving to upper left corner, set wih max_offset
    max_offset = 2000
    vertical_step = 250
    cross_align.cross_scan_primary.move_to_position(0, 0)
    time.sleep(30)
    cross_align.cross_scan_primary.scan_window(max_offset, vertical_step)

    # cross_align.lock.acquire()
    # cross_align.client.home()  # home primary unit
    # cross_align.lock.release()
    # time.sleep(30)
    # cross_align.cross_scan_secondary.scan_window(max_offset, vertical_step)

    cross_align.heatmap_primary.clear_heatmap()  # clear heatmap
    cross_align.heatmap_secondary.clear_heatmap()  # clear heatmap

    # move both to max position
    cross_align.move_primary_to_max()  # move to position where other unit rx was highest
    cross_align.move_secondary_to_max()  # move to position where other unit rx was highest

    # repeat a few times
    prev_primary_max = None
    prev_secondary_max = None
    for i in range(0, 4):
        steps = [2500, 1000, 500, 100]

        for step in steps:
            print(f"================= MOVING FOR {step} =================")
            # start doing crosses on main
            cross_align.cross_scan_primary.do_cross(step)
            cross_align.heatmap_primary.clear_heatmap()  # clear heatmap

            # start doing crosses on main
            cross_align.cross_scan_secondary.do_cross(step)
            cross_align.heatmap_secondary.clear_heatmap()  # clear heatmap

            cross_align.move_primary_to_max()  # move to position where other unit rx was highest
            cross_align.move_secondary_to_max()  # move to position where other unit rx was highest

            if prev_primary_max == cross_align.max_point_primary:
                print("=============== MOVING PRIMARY OUT OF LOCAL MAXIMUM ==================")
                cross_align.spiral_scan_primary.do_spiral(750, 5)  # do spiral
                # return to max pos
                cross_align.move_primary_to_max()
                # random_x = random.randrange(-500, 500, 150)
                # random_y = random.randrange(-500, 500, 150)
                # cross_align.cross_scan_primary.move_to_position(cross_align.max_point_primary["x"] + random_x, cross_align.max_point_primary["y"] + random_y)

            if prev_secondary_max == cross_align.max_point_secondary:
                print("=============== MOVING SECONDARY OUT OF LOCAL MAXIMUM ==================")
                cross_align.spiral_scan_secondary.do_spiral(750, 5)
                # return to max pos
                cross_align.move_secondary_to_max()
                # random_x = random.randrange(-500, 500, 150)
                # random_y = random.randrange(-500, 500, 150)
                # cross_align.cross_scan_secondary.move_to_position(cross_align.max_point_secondary["x"] + random_x, cross_align.max_point_secondary["y"] + random_y)

            prev_primary_max = cross_align.max_point_primary
            prev_secondary_max = cross_align.max_point_secondary

align_primary_secondary()