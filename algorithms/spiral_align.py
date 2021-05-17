import xmlrpc.client
import time
import logging
from threading import Thread, Lock

from ..src.align import Align, Unit
from ..src.strategy import Strategy
from ..src.heatmap import Heatmap

# TODO read offset positions from file
offset_x_master = 282
offset_y_master = 528

offset_x_slave = 462
offset_y_slave = 292

log = logging.getLogger()

class Direction():
    LEFT = {"name": "left", "dir": -1}
    RIGHT = {"name": "right", "dir": 1}
    DOWN = {"name": "down", "dir": -1}
    UP = {"name": "up", "dir": 1}

# READ THIS: https://realpython.com/python-interface/
class SpiralAlign(Align):
    def __init__(self, heatmap_primary, heatmap_secondary):
        """Init algorithm variables"""
        super().__init__()

        self.heatmap_primary = heatmap_primary
        self.heatmap_secondary = heatmap_secondary

        self.current_target = {
            "primary": None,
            "secondary": None
        }

        self.set_max_point_strategy(Strategy.LOCAL_MAX)
        self.start_monitoring()

    def __del__(self):
        """Destructor"""
        pass

    def next_step(self, unit, direction_enum, step, rx_power_limit):
        """Move in horizontal/vertical direction"""

        print(f"Moving in direction: {direction_enum} on {unit}")
        skip = False

        direction = direction_enum["dir"]

        if self.current_state[unit]["dBm"] > rx_power_limit:
            print("REACHED LINK ALIGNMENT - BREAKING OUT")
            return 
        
        self.current_target[unit] = self.current_state[unit].copy()

        print(f"Current state of {unit}: {self.current_state[unit]}")

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

        print(f"Current target of {unit}: {self.current_target[unit]}")
        if not skip:
            self.move_to_position(unit, self.current_target[unit]["x"], self.current_target[unit]["y"], rx_power_limit)

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

    def do_spiral(self, unit, step_size, stop_after=5, no_max_limit=5, rx_power_limit=-3):
        """Do spiral until at circle_limit"""
        step = 0
        circle_count = 0  #

        if self.current_state[unit]["dBm"] > rx_power_limit:
            print("REACHED LINK ALIGNMENT - BREAKING OUT")
            return

        while circle_count < stop_after:

            step += step_size
            self.next_step(unit, Direction.LEFT, step, rx_power_limit)
            self.next_step(unit, Direction.UP, step, rx_power_limit)

            step += step_size
            self.next_step(unit, Direction.RIGHT, step, rx_power_limit)
            self.next_step(unit, Direction.DOWN, step, rx_power_limit)

            circle_count += 1

    def align_alternatingly(self, rx_power_limit=0):
        """Align to each units max power"""

        # 1. Start by homing
        self.move_to_position(Unit.PRIMARY, 0, 0, rx_power_limit)
        self.move_to_position(Unit.SECONDARY, 0, 0, rx_power_limit)

        self.heatmap_primary.clear_heatmap()  # clear heatmap
        self.heatmap_secondary.clear_heatmap()  # clear heatmap

        # move both to max position
        
        self.move_to_max(Unit.PRIMARY, rx_power_limit)
        self.move_to_max(Unit.SECONDARY, rx_power_limit)

        # 2. repeat steps until limit is reached or signal strength is satisfactory
        LOOP_COUNT_LIMIT = 5
        N = 4
        loop_count = 0

        print("STARTING LOOP")

        while (self.current_state["primary"]["dBm"] < rx_power_limit and self.current_state["secondary"]["dBm"] < rx_power_limit) and loop_count < LOOP_COUNT_LIMIT:

            step_size = 1000

            if self.current_state["primary"]["dBm"] > -20 or self.current_state["secondary"]["dBm"] > -20:
                step_size = 1000

            if self.current_state["primary"]["dBm"] > -15 or self.current_state["secondary"]["dBm"] > -15:
                step_size = 500

            if self.current_state["primary"]["dBm"] > -10 or self.current_state["secondary"]["dBm"] > -10:
                step_size = 250

            rx_power_limit = -3
            for _ in range(0, N):
                # reset max so we're not stuck on incorrect maxima
                self.reset_maximum(Unit.PRIMARY)
                self.reset_maximum(Unit.SECONDARY)
                self.do_spiral(Unit.PRIMARY, step_size, stop_after=5, rx_power_limit=rx_power_limit)
                self.move_to_max(Unit.PRIMARY, rx_power_limit)
                # self.move_to_max(Unit.SECONDARY)
                self.do_spiral(Unit.SECONDARY, step_size, stop_after=5, rx_power_limit=rx_power_limit)
                # self.move_to_max(Unit.PRIMARY)
                self.move_to_max(Unit.SECONDARY, rx_power_limit)
                print(f"======= SPIRAL SCAN WITH STEP {step_size} FINISHED =======")
                step_size = int(step_size * 0.75)

            loop_count += 1


# create heatmaps
heatmap_primary = Heatmap(offset_x_master, offset_y_master)
heatmap_secondary = Heatmap(offset_x_slave, offset_y_slave)

spiral_align = SpiralAlign(heatmap_primary, heatmap_secondary)
spiral_align.align_alternatingly()
