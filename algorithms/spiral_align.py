import xmlrpc.client
import time
import logging
from threading import Thread, Lock

from ..src.heatmap import Heatmap
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

class SpiralAlign():
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

        self.spiral_scan_primary = SpiralScan(self.client, 0, 0, remote=False, lock=self.lock)
        self.spiral_scan_secondary = SpiralScan(self.client, 0, 0, remote=True, lock=self.lock)

        self.running = True

        self.monitor_thread = Thread(target=self.get_unit_diagnostics, daemon=True)
        self.monitor_thread.start()

    def __del__(self):
        """Destructor"""
        self.running = False
        self.monitor_thread.join()

    def move_to_max_position_primary(self):
        """Move to currently saved max position"""
        self.spiral_scan_primary.move_to_position(self.max_point_primary["x"], self.max_point_primary["y"])

    def move_to_max_position_secondary(self):
        """Move to currently saved max position"""
        self.spiral_scan_primary.move_to_position(self.max_point_secondary["x"], self.max_point_secondary["y"])

    def get_unit_diagnostics(self):
        """Get both unit diagnostics in a short interval"""

        while self.running:
            self.lock.acquire()

            try:
                pos_x_secondary, pos_y_secondary = self.client.issue_remote_command("get_motors_position", ())
                rx_dBm_secondary = self.client.issue_remote_command("get_sfp_diagnostics", ())["sfp_0"]["diagnostics"]["rx_power_dBm"]

                pos_x_primary, pos_y_primary = self.client.get_motors_position()
                rx_dBm_primary = self.client.get_sfp_diagnostics()["sfp_0"]["diagnostics"]["rx_power_dBm"]

                if rx_dBm_secondary > self.max_point_secondary["dBm"] or rx_dBm_primary > self.max_point_primary["dBm"]:

                    # update max points if total dBm is higher than previously
                    if rx_dBm_primary + rx_dBm_secondary > self.max_point_primary["dBm"] + self.max_point_secondary["dBm"]:
                        self.max_point_secondary = {"x": pos_x_secondary, "y": pos_x_secondary, "dBm": rx_dBm_secondary}
                        print(f"New max point on secondary unit: {self.max_point_secondary}")

                        # update both max points! - since max depends on both positions, not only one
                        self.max_point_primary = {"x": pos_x_primary, "y": pos_y_primary, "dBm": rx_dBm_primary}
                        print(f"New max point on primary unit: {self.max_point_primary}")

                self.heatmap_primary.add_point(pos_x_primary, pos_y_primary, rx_dBm_primary)
                self.heatmap_secondary.add_point(pos_x_secondary, pos_y_secondary, rx_dBm_secondary)
                
            except Exception as e:
                log.error(f"Error getting rx_dBm: {e}")

            self.lock.release()

            time.sleep(0.2)

def align_step_async(spiral_align, step_size, stop_after):
    """One iteration of alignment:
        * primary move & secondary move
        * move both to max
    """

    align_primary_thread = Thread(target=align_step_primary, args=(spiral_align, step_size, stop_after))
    align_primary_thread.start()
    align_secondary_thread = Thread(target=align_step_secondary, args=(spiral_align, step_size, stop_after))
    align_secondary_thread.start()

    align_primary_thread.join()
    align_secondary_thread.join()
    
    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


def align_step_primary(spiral_align, step_size, stop_after=5):
    """Do step of alignment on primary unity"""

    spiral_align.spiral_scan_primary.do_spiral(step_size, stop_after=stop_after)
    spiral_align.heatmap_primary.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.txt")
    spiral_align.heatmap_primary.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.jpg", size=1)
    spiral_align.heatmap_primary.clear_heatmap()  # clear heatmap
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])

def align_step_secondary(spiral_align, step_size, stop_after=5):
    """Do step of alignment on secondary unit"""
    spiral_align.spiral_scan_secondary.do_spiral(step_size, stop_after=stop_after)
    spiral_align.heatmap_secondary.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_master}_slave.txt")
    spiral_align.heatmap_secondary.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_master}_slave.jpg", size=1)
    spiral_align.heatmap_secondary.clear_heatmap()  # clear heatmap
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])

def align_asnyc():
    """Align units asynchronously"""
    spiral_align = SpiralAlign(heatmap_primary, heatmap_secondary)

    # 1. Start by homing
    spiral_align.lock.acquire()
    spiral_align.client.home()
    spiral_align.lock.release()
    spiral_align.lock.acquire()
    spiral_align.client.issue_remote_command("home", ())
    spiral_align.lock.release()

    spiral_align.heatmap_primary.clear_heatmap()  # clear heatmap
    spiral_align.heatmap_secondary.clear_heatmap()  # clear heatmap

    time.sleep(30)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])

    # align_step_async(spiral_align, step_size=2500, stop_after=2)
    align_step_async(spiral_align, step_size=750, stop_after=7)
    align_step_async(spiral_align, step_size=500, stop_after=10)
    align_step_async(spiral_align, step_size=250, stop_after=10)

    # try to repeat maybe?
    align_step_async(spiral_align, step_size=100, stop_after=30)
    align_step_async(spiral_align, step_size=100, stop_after=20)
    align_step_async(spiral_align, step_size=100, stop_after=10)

def align_primary_secondary():
    """Align so primary is aligned first and secondary later"""
    spiral_align = SpiralAlign(heatmap_primary, heatmap_secondary)

    # 1. Start by homing
    spiral_align.lock.acquire()
    spiral_align.client.home()
    spiral_align.lock.release()
    spiral_align.lock.acquire()
    spiral_align.client.issue_remote_command("home", ())
    spiral_align.lock.release()

    spiral_align.heatmap_primary.clear_heatmap()  # clear heatmap
    spiral_align.heatmap_secondary.clear_heatmap()  # clear heatmap

    time.sleep(30)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])

    # align primary unit
    step_size = 750
    align_step_primary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    step_size = 500
    align_step_primary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    step_size = 250
    align_step_primary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    step_size = 100
    align_step_primary(spiral_align, step_size, stop_after=10)
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    align_step_primary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    align_step_primary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    

    step_size = 750
    align_step_secondary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])
    step_size = 500
    align_step_secondary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])
    step_size = 250
    align_step_secondary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])
    step_size = 100
    align_step_secondary(spiral_align, step_size, stop_after=10)
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])
    align_step_secondary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])
    align_step_secondary(spiral_align, step_size, stop_after=5)
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


def align_alternatingly():
    """Align to each units max power"""
    spiral_align = SpiralAlign(heatmap_primary, heatmap_secondary)

    # 1. Start by homing
    spiral_align.lock.acquire()
    spiral_align.client.home()
    spiral_align.lock.release()
    spiral_align.lock.acquire()
    spiral_align.client.issue_remote_command("home", ())
    spiral_align.lock.release()

    spiral_align.heatmap_primary.clear_heatmap()  # clear heatmap
    spiral_align.heatmap_secondary.clear_heatmap()  # clear heatmap

    time.sleep(30)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])

    step_size = 750
    align_step_primary(spiral_align, step_size, stop_after=7)
    align_step_secondary(spiral_align, step_size, stop_after=7)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


    step_size = 500
    align_step_primary(spiral_align, step_size, stop_after=10)
    align_step_secondary(spiral_align, step_size, stop_after=10)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


    step_size = 250
    align_step_primary(spiral_align, step_size, stop_after=10)
    align_step_secondary(spiral_align, step_size, stop_after=10)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


    step_size = 100
    align_step_primary(spiral_align, step_size, stop_after=30)
    align_step_secondary(spiral_align, step_size, stop_after=30)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


    step_size = 100
    align_step_primary(spiral_align, step_size, stop_after=20)
    align_step_secondary(spiral_align, step_size, stop_after=20)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])


    step_size = 100
    align_step_primary(spiral_align, step_size, stop_after=10)
    align_step_secondary(spiral_align, step_size, stop_after=10)

    # move both to max position
    spiral_align.spiral_scan_primary.move_to_position(spiral_align.max_point_primary["x"], spiral_align.max_point_primary["y"])
    spiral_align.spiral_scan_secondary.move_to_position(spiral_align.max_point_secondary["x"], spiral_align.max_point_secondary["y"])

# align_alternatingly()
# align_asnyc()
align_primary_secondary()