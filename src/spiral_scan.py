import time
import logging

log = logging.getLogger()

range_x = 14000
range_y = 14000
z_min = -40
z_max = 2

LEFT = {"name": "left", "direction": "-1"}
RIGHT = {"name": "right", "direction": "1"}
DOWN = {"name": "down", "direction": "-1"}
UP = {"name": "up", "direction": "1"}

IMG_FOLDER = "/home/pi/koruza_v2/koruza_v2_tracking/images/"

class SpiralScan():
    def __init__(self, client, heatmap):
        """Initialize spiral scan class"""
        # initialize rpc client
        # self.client = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)

        self.client = client

        self.current_target_x = None
        self.current_target_y = None

        self.heatmap = heatmap  # heatmap if the user wants data plotted

        self.max_point = None  # max point (x, y, rx_pow)

    def next_step(self, direction_enum, step):
        """Move in horizontal/vertical direction"""

        prev_max_rx_dBm = -100

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

                # update max point
                if rx_dBm > prev_max_rx_dBm:
                    self.max_point (pos_x, pos_y, rx_dBm)
                    prev_max_rx_dBm = rx_power_dBm

                # write rx_dBm to heatmap
                self.heatmap.add_point(pos_x, pos_y, rx_dBm)
                print(f"Pos x: {pos_x}, pos y: {pos_y}")

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

                if pos_x > 14000 or pos_x < -14000 or pos_y > 14000 or pos_y < -14000:
                    continue 

                if count_not_changed >= 30:  # TODO find good number
                    print("Break out in count not chagned")
                    break

                if (pos_x == self.current_target_x and self.current_target_y == pos_y) or (pos_x <= -range_x or pos_x >= range_x) or (pos_y <= -range_y or pos_y >= range_y):
                    print("Break out in correct position found")
                    break
                time.sleep(0.5)
            
            end_time = time.time()

            print(f"Step size {step} duration: {end_time - start_time}")


    def do_spiral(self, step_size, start_pos_x=None, start_pos_y=None, stop_after=5, no_max_limit=5, rx_power_limit=-35):
        """Do spiral until at circle_limit"""
        step = 0
        not_found_count = 0

        if start_pos_x is not None and start_pos_y is not None:
            self.current_target_x = start_pos_x
            self.current_target_y = start_pos_y

            self.client.move_motors_to(start_pos_x, start_pos_y)
            
            pos_x, pos_y = self.client.get_motors_position()
            while self.current_target_x != pos_x and self.current_target_y != pos_y:
                time.sleep(0.5)  # sleep until motor moves to desired position
        else:
            self.current_target_x, self.current_target_y = self.client.get_motors_position()

        circle_count = 0  # 
        while circle_count < stop_after:
            step += step_size
            self.next_step(LEFT, step)
            self.next_step(UP, step)

            step += step_size
            self.next_step(RIGHT, step)
            self.next_step(DOWN, step)

            circle_count += 1
            pos_x, pos_y, rx_power_dBm = self.max_point

            if rx_power_dBm < rx_power_limit:
                not_found_count += 1
            else:
                not_found_count = 0

            if not_found_count >= no_max_limit:  # if not found after 5 cycles break - TODO is this ok? - should w
                break

    def get_max_position(self):
        """Return position of maximum power and read power"""
        return self.max_point