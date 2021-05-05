import xmlrpc.client
import time
import logging
from threading import Thread, Lock

from ..src.align import Align, Unit, Strategy
from ..src.heatmap import Heatmap

# TODO read offset positions from file
offset_x_master = 282
offset_y_master = 528

offset_x_slave = 462
offset_y_slave = 292

heatmap_primary = Heatmap(offset_x_master, offset_y_master)
heatmap_secondary = Heatmap(offset_x_slave, offset_y_slave)

log = logging.getLogger()

class Direction():
    LEFT = {"name": "left", "dir": -1}
    RIGHT = {"name": "right", "dir": 1}
    DOWN = {"name": "down", "dir": -1}
    UP = {"name": "up", "dir": 1}


class SpiralAlign(Align):
    def __init__(self, heatmap_primary, heatmap_secondary):
        """Init algorithm variables"""
        super().__init__()

        self.heatmap_primary = heatmap_primary
        self.heatmap_secondary = heatmap_secondary

        self.current_target = {
            "primary": {
                "x": 0,
                "y": 0
            },
            "secondary": {
                "x": 0,
                "y": 0
            }
        }
        self.set_max_point_strategy(Strategy.LOCAL_MAX)
        self.start_monitoring()

    def __del__(self):
        """Destructor"""
        pass

    def next_step(self, unit, direction_enum, step):
        """Move in horizontal/vertical direction"""

        print(f"Moving in direction: {direction_enum} on {unit}")
        skip = False

        direction = direction_enum["dir"]

        if direction_enum == Direction.LEFT or direction_enum == Direction.RIGHT:
            self.current_target[unit]["x"] += direction * step

        if direction_enum == Direction.UP or direction_enum == Direction.DOWN:
            self.current_target[unit]["y"] += direction * step

        if self.current_target[unit]["x"] > 12500 or self.current_target[unit]["x"] < -12500:
            skip = True
            self.current_target[unit]["x"] -= direction * step
        
        if self.current_target[unit]["y"] > 12500 or self.current_target[unit]["y"] < -12500:
            skip = True
            self.current_target[unit]["y"] -= direction * step

        if not skip:
            self.move_to_position(unit, self.current_target[unit]["x"], self.current_target[unit]["y"])

    def do_inward_spiral(self, unit):
        """Do inward spiral from 12500,12500 to 0,0"""
        steps = range(24000, 0, -1000)
        # steps = [24000, 22000, 20000, 18000, 16000, 14000, 12000, 10000, 8000, 6000, 4000, 2000, 1000, 500, 250, 100]
        step_index = 0

        while True:
            step = steps[step_index]
            self.next_step(unit, Direction.RIGHT, step)
            self.next_step(unit, Direction.DOWN, step)
            step_index += 1
            if step_index >= len(steps):
                break  # stop loop if past last index

            step = steps[step_index]
            self.next_step(unit, Direction.LEFT, step)
            self.next_step(unit, Direction.UP, step)
            step_index += 1
            if step_index >= len(steps):
                break  # stop loop if past last index

    def do_spiral(self, unit, step_size, stop_after=5, no_max_limit=5, rx_power_limit=-35):
        """Do spiral until at circle_limit"""
        step = 0
        circle_count = 0  #

        while circle_count < stop_after:
            step += step_size
            self.next_step(unit, Direction.LEFT, step)
            self.next_step(unit, Direction.UP, step)

            step += step_size
            self.next_step(unit, Direction.RIGHT, step)
            self.next_step(unit, Direction.DOWN, step)

            circle_count += 1


    def align_alternatingly(self):
        """Align to each units max power"""

        # 1. Start by homing
        self.move_to_position(Unit.PRIMARY, 0, 0)
        self.move_to_position(Unit.SECONDARY, 0, 0)

        self.heatmap_primary.clear_heatmap()  # clear heatmap
        self.heatmap_secondary.clear_heatmap()  # clear heatmap

        # move both to max position
        self.move_to_max(Unit.PRIMARY)
        self.move_to_max(Unit.SECONDARY)

        # 2. repeat steps until limit is reached or signal strength is satisfactory
        LOOP_COUNT_LIMIT = 5

        while (self.max["primary"]["dBm"] < -10 and self.max["secondary"]["dBm"] < -10) or loop_count > LOOP_COUNT_LIMIT:

            step_size = 750
            self.do_spiral(Unit.PRIMARY, step_size, stop_after=5)
            self.do_spiral(Unit.SECONDARY, step_size, stop_after=5)

            # move both to max position
            self.move_to_max(Unit.PRIMARY)
            self.move_to_max(Unit.SECONDARY)

            step_size = 250
            self.do_spiral(Unit.PRIMARY, step_size, stop_after=7)
            self.do_spiral(Unit.SECONDARY, step_size, stop_after=7)

            # move both to max position
            self.move_to_max(Unit.PRIMARY)
            self.move_to_max(Unit.SECONDARY)

            step_size = 100
            self.do_spiral(Unit.PRIMARY, step_size, stop_after=10)
            self.do_spiral(Unit.SECONDARY, step_size, stop_after=10)

            # move both to max position
            self.move_to_max(Unit.PRIMARY)
            self.move_to_max(Unit.SECONDARY)

            loop_count += 1

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
    spiral_align.spiral_scan_primary.move_to_position(0, 0)
    spiral_align.spiral_scan_secondary.move_to_position(0, 0)

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
    spiral_align.move_to_max(Unit.PRIMARY)
    spiral_align.move_to_max(Unit.SECONDARY)

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



spiral_align = SpiralAlign(heatmap_primary, heatmap_secondary)
spiral_align.align_alternatingly()

# align_alternatingly()
# align_asnyc()
# align_primary_secondary()