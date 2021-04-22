import time
import logging
import numpy as np
from enum import Enum
# import matplotlib.pyplot as plt

import xmlrpc.client
from ...src.constants import KORUZA_MAIN_PORT

log = logging.getLogger()

range_x = 14000
range_y = 14000

LEFT = {"name": "left", "direction": "-1"}
RIGHT = {"name": "right", "direction": "1"}
DOWN = {"name": "down", "direction": "-1"}
UP = {"name": "up", "direction": "1"}

class Heatmap():
    def __init__(self):
        """Heatmap class"""
        self.heatmap = []

    def add_point(self, pos_x, pos_y, rx_dBm):
        """Append new point to heatmap array"""
        point = (pos_x, pos_y, rx_dBm)
        self.heatmap.append(point)

    def find_max_of_heatmap(self):
        """Get pos_x and pos_y of heatmap"""

        max_val = -100
        selected_index = 0
        for index, point in enumerate(self.heatmap):
            if point[2] > max_val:
                selected_index = index

        print(f"Selected index: {selected_index}")

        return self.heatmap[selected_index]  # return selected point

    def clear_heatmap(self):
        """Clear entire heatmap"""
        self.heatmap = []


class SpiralScan():
    def __init__(self):
        """Initialize spiral scan class"""
        # initialize rpc client
        self.client = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)

        self.current_target_x = None
        self.current_target_y = None

        self.heatmap = Heatmap()


    def next_step(self, direction_enum, step):
        """Move in horizontal/vertical direction"""

        print(f"Moving in direction: {direction_enum}")
        direction = int(direction_enum["direction"])

        skip = False

        if direction_enum == LEFT or direction_enum == RIGHT:
            self.current_target_x += direction * step

        if direction_enum == UP or direction_enum == DOWN:
            self.current_target_y += direction * step

        if self.current_target_x > 12500 or self.current_target_x < -12500:
            skip = True
            self.current_target_x -= direction * step
        
        if self.current_target_y > 12500 or self.current_target_y < -12500:
            skip = True
            self.current_target_y -= direction * step

        if not skip:
            if direction_enum == LEFT or direction_enum == RIGHT:
                self.client.move_motors(direction * step, 0, 0)
            if direction_enum == UP or direction_enum == DOWN:
                self.client.move_motors(0, direction * step, 0)

            start_time = time.time()
            count_not_changed = 0  # if read values does not change for x reads break out of loop
            prev_pos_x = None
            prev_pos_y = None
            # wait for motors to move
            for _ in range(0, 1000):  # wait for motors to move to position - TODO find actual time range
                # TODO implement stuck check
                pos_x, pos_y = self.client.get_motors_position()

                rx_dBm = -40
                try:
                    rx_dBm = self.client.get_sfp_diagnostics()["sfp_0"]["diagnostics"]["rx_power_dBm"]
                    # print(rx_dBm)
                except Exception as e:
                    log.error(f"Error getting rx_dBm: {e}")

                # write rx_dBm to heatmap
                self.heatmap.add_point(pos_x, pos_y, rx_dBm)

                if prev_pos_x == pos_x:
                    count_not_changed += 1
                else:
                    count_not_changed = 0

                if prev_pos_y == pos_y:
                    count_not_changed += 1
                else:
                    count_not_changed = 0

                prev_pos_x = pos_x
                prev_pos_y = pos_y


                if count_not_changed >= 5:  # TODO find good number
                    print("Break out in count not chagned")
                    break

                if pos_x > 14000 or pos_x < -14000 or pos_y > 14000 or pos_y < -14000:
                    
                    continue 

                print(f"Pos x: {pos_x}, pos y: {pos_y}")

                if (pos_x == self.current_target_x and self.current_target_y == pos_y) or (pos_x <= -range_x or pos_x >= range_x) or (pos_y <= -range_y or pos_y >= range_y):
                    print("Break out in correct position found")
                    break
                time.sleep(0.5)
            
            end_time = time.time()

            print(f"Step size {step} duration: {end_time - start_time}")


    def do_spiral(self, step_limit, step, step_size, start_pos_x=None, start_pos_y=None):
        """Do spiral until at 12500, 12500"""

        if start_pos_x is not None and start_pos_y is not None:
            self.current_target_x = start_pos_x
            self.current_target_y = start_pos_y

            self.client.move_motors_to(start_pos_x, start_pos_y)
            
            pos_x, pos_y = self.client.get_motors_position()
            while self.current_target_x != pos_x and self.current_target_y != pos_y:
                time.sleep(0.5)  # sleep until motor moves to desired position
        else:
            self.current_target_x, self.current_target_y = self.client.get_motors_position()

        not_found_count = 0  # 
        while step <= step_limit:
            step += step_size
            self.next_step(LEFT, step)
            self.next_step(UP, step)
            step += step_size
            self.next_step(RIGHT, step)
            self.next_step(DOWN, step)

            pos_x, pos_y, rx_power_dBm = self.heatmap.find_max_of_heatmap()  # find max power after one cycle

            if rx_power_dBm < -35:
                not_found_count += 1
            else:
                not_found_count = 0

            if not_found_count >= 5:  # if not found after 5 cycles break
                break

    def align(self):
        """Align to max power"""
        self.do_spiral(12500, 0, 1000)  # make spiral of 1000

        pos_x, pos_y, rx_power_dBm = self.heatmap.find_max_of_heatmap()
        print(f"Found maximum at: {pos_x}, {pos_y}: {rx_power_dBm}")

        self.heatmap.clear_heatmap()  # clear heatmap

        self.do_spiral(2500, 0, 100, pos_x, pos_y)  # do second spiral and move to max pos

        pos_x, pos_y, rx_power_dBm = self.heatmap.find_max_of_heatmap()
        print(f"Found maximum at: {pos_x}, {pos_y}: {rx_power_dBm}")

        self.client.move_motors_to(pos_x, pos_y)


# 0.) manually align cross to second unit camera (auto align later down the road)

# 2.) move in spiral from START_X, START_Y to max, max in step of 1000
# keep track of all positions and values for heatmap
# https://numpy.org/doc/stable/reference/routines.array-creation.html#routines-array-creation

spiral = SpiralScan()
spiral.align()