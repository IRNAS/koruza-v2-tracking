import xmlrpc.client

from ..src.heatmap import Heatmap
from ..src.spiral_scan import SpiralScan

from ...src.constants import KORUZA_MAIN_PORT

# draw according to start offset of marker
# TODO read from file
offset_x = 290
offset_y = 534

heatmap_primary = Heatmap(offset_x, offset_y)
heatmap_secondary = Heatmap(offset_x, offset_y)

client_primary = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)
client_secondary = xmlrpc.client.ServerProxy(f"http://192.168.13.226:{KORUZA_MAIN_PORT}", allow_none=True)

primary = SpiralScan(client_primary, heatmap_primary)
secondary = SpiralScan(client_secondary, heatmap_secondary)

def align_alternatingly():
    """Align to max power"""
    step_size = 2500
    primary.do_spiral(step_size, stop_after=2)  # make spiral of 2500
    pos_x, pos_y, rx_power_dBm = primary.get_max_position()
    print(f"Found maximum at: {pos_x}, {pos_y}: {rx_power_dBm}")
    primary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x}_{offset_y}.txt")
    primary.heatmap.save_image(f"step_{step_size}_{offset_x}_{offset_y}.jpg", size=1)
    primary.heatmap.clear_heatmap()  # clear heatmap

    secondary.do_spiral(step_size, stop_after=2)  # make spiral of 2500
    pos_x, pos_y, rx_power_dBm = secondary.get_max_position()
    print(f"Found maximum at: {pos_x}, {pos_y}: {rx_power_dBm}")
    secondary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x}_{offset_y}.txt")
    secondary.heatmap.save_image(f"step_{step_size}_{offset_x}_{offset_y}.jpg", size=1)
    secondary.heatmap.clear_heatmap()  # clear heatmap

    step_size = 1000
    primary.do_spiral(step_size, stop_after=2)  # make spiral of 1000
    pos_x, pos_y, rx_power_dBm = primary.get_max_position()
    print(f"Found maximum at: {pos_x}, {pos_y}: {rx_power_dBm}")
    primary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x}_{offset_y}.txt")
    primary.heatmap.save_image(f"step_{step_size}_{offset_x}_{offset_y}.jpg", size=1)
    primary.heatmap.clear_heatmap()  # clear heatmap

    secondary.do_spiral(step_size, stop_after=2)  # make spiral of 1000
    pos_x, pos_y, rx_power_dBm = secondary.get_max_position()
    print(f"Found maximum at: {pos_x}, {pos_y}: {rx_power_dBm}")
    secondary.heatmap.save_heatmap_data(f"step_{step_size}_{offset_x}_{offset_y}.txt")
    secondary.heatmap.save_image(f"step_{step_size}_{offset_x}_{offset_y}.jpg", size=1)
    secondary.heatmap.clear_heatmap()  # clear heatmap