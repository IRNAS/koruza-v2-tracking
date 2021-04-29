import xmlrpc.client
import time
from threading import Thread

from ..src.heatmap import Heatmap
from ..src.spiral_scan import SpiralScan

from ...src.constants import KORUZA_MAIN_PORT, DEVICE_MANAGEMENT_PORT

# draw according to start offset of marker
# TODO read from file
offset_x_master = 282
offset_y_master = 528

offset_x_slave = 462
offset_y_slave = 292

heatmap_primary = Heatmap(offset_x_master, offset_y_master)
heatmap_secondary = Heatmap(offset_x_slave, offset_y_slave)

client_primary = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)  # client to koruza
time.sleep(3)
primary = SpiralScan(client_primary, heatmap_primary)
secondary = SpiralScan(client_primary, heatmap_secondary, remote=True)

def inward_spiral_primary_thread():
    """Start thread for inward spiral on primary unit"""
    primary.move_to_position(-12000, 12000)  # move to upper leftern corner
    primary.do_inward_spiral()
    primary.move_to_max_position()

def inward_spiral_secondary_thread():
    """Start thread for inward spiral on secondary unit"""
    secondary.move_to_position(-12000, 12000)
    secondary.do_inward_spiral()
    secondary.move_to_max_position()

def align_alternatingly():
    """Align to max power"""
    # primary.move_to_position(-12000, 12000)  # move to upper leftern corner
    # primary.do_inward_spiral()
    # primary.move_to_max_position()

    # secondary.move_to_position(-12000, 12000)
    # secondary.do_inward_spiral()
    # secondary.move_to_max_position()

    # start by roughly aligning calibrated units

    step_size = 500
    primary.do_spiral(step_size, stop_after=5)  # make spiral of 1000
    primary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.txt")
    primary.heatmap.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.jpg", size=1)
    primary.heatmap.clear_heatmap()  # clear heatmap
    primary.move_to_max_position()

    secondary.do_spiral(step_size, stop_after=5)  # make spiral of 1000
    secondary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_slave}_slave.txt")
    secondary.heatmap.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_slave}_slave.jpg", size=1)
    secondary.heatmap.clear_heatmap()  # clear heatmap
    secondary.move_to_max_position()


    step_size = 250
    primary.do_spiral(step_size, stop_after=5)  # make spiral of 250
    primary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.txt")
    primary.heatmap.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.jpg", size=1)
    primary.heatmap.clear_heatmap()  # clear heatmap
    primary.move_to_max_position()

    secondary.do_spiral(step_size, stop_after=5)  # make spiral of 250
    secondary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_slave}_slave.txt")
    secondary.heatmap.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_slave}_slave.jpg", size=1)
    secondary.heatmap.clear_heatmap()  # clear heatmap
    secondary.move_to_max_position()

    step_size = 100
    primary.do_spiral(step_size, stop_after=5)  # make spiral of 250
    primary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.txt")
    primary.heatmap.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_master}_master.jpg", size=1)
    primary.heatmap.clear_heatmap()  # clear heatmap
    primary.move_to_max_position()

    secondary.do_spiral(step_size, stop_after=5)  # make spiral of 250
    secondary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x_master}_{offset_y_slave}_slave.txt")
    secondary.heatmap.save_image(f"step_{step_size}_{offset_x_master}_{offset_y_slave}_slave.jpg", size=1)
    secondary.heatmap.clear_heatmap()  # clear heatmap
    secondary.move_to_max_position()

align_alternatingly()