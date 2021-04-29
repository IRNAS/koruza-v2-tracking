import time
import logging
from threading import Lock

log = logging.getLogger()

range_x = 14000
range_y = 14000

LEFT = {"name": "left", "direction": "-1"}
RIGHT = {"name": "right", "direction": "1"}
DOWN = {"name": "down", "direction": "-1"}
UP = {"name": "up", "direction": "1"}

IMG_FOLDER = "/home/pi/koruza_v2/koruza_v2_tracking/images/"

class SpiralScan():
    def __init__(self, client, heatmap, remote=None):
        """Initialize spiral scan class"""
        # initialize rpc client
        # self.client = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)

        self.client = client

        self.current_target_x = None
        self.current_target_y = None

        self.heatmap = heatmap  # heatmap if the user wants data plotted

        self.remote = remote

        self.start_pos_x = None
        self.start_pos_y = None

        self.lock = Lock()

        
        if self.remote:
            self.start_pos_x, self.start_pos_y = self.client.issue_remote_command("get_motors_position", ())
        else:
            self.start_pos_x, self.start_pos_y = self.client.get_motors_position()
        
        self.max_point = {"x": self.start_pos_x, "y": self.start_pos_y, "dBm": -40}  # max point (x, y, rx_pow)
        self.prev_max_point = {"x": self.start_pos_x, "y": self.start_pos_y, "dBm": -40}
        
        self.new_max_found = False

    def next_step(self, direction_enum, step):
        """Move in horizontal/vertical direction"""

        # get current position
        
        if self.remote:
            self.current_target_x, self.current_target_y = self.client.issue_remote_command("get_motors_position", ())
        else:
            self.current_target_x, self.current_target_y = self.client.get_motors_position()
        

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
            if self.remote:
                self.client.issue_remote_command("move_motors_to", (self.current_target_x, self.current_target_y))
            else:
                self.client.move_motors_to(self.current_target_x, self.current_target_y)               

            start_time = time.time()
            count_not_changed = 0  # if read values does not change for x reads break out of loop
            prev_pos_x = None
            prev_pos_y = None
                
            # wait for motors to move
            for _ in range(0, 1000):  # wait for motors to move to position - TODO find actual time range
                # TODO implement stuck check
                # print(f"Current target x: {self.current_target_x}, {self.current_target_y}")
                try:
                    if self.remote:
                        pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
                    else:
                        pos_x, pos_y = self.client.get_motors_position()

                    # print(f"Read pos x: {pos_x}, pos y: {pos_y}")
                except Exception as e:
                    log.error(f"An error occured when unpacking motor position values: {e}")
                    
                if self.remote:
                    try:
                        rx_dBm = self.client.issue_remote_command("get_sfp_diagnostics", ())["sfp_0"]["diagnostics"]["rx_power_dBm"]
                        # print(rx_dBm)
                    except Exception as e:
                        log.error(f"Error getting rx_dBm: {e}")
                else:
                    try:
                        rx_dBm = self.client.get_sfp_diagnostics()["sfp_0"]["diagnostics"]["rx_power_dBm"]
                        # print(rx_dBm)
                    except Exception as e:
                        log.error(f"Error getting rx_dBm: {e}")
                

                # update max point
                if rx_dBm > self.prev_max_point["dBm"]:
                    self.max_point = {"x": pos_x, "y": pos_y, "dBm": rx_dBm}
                    print(f"New max point: {self.max_point}")
                    self.prev_max_point = self.max_point
                    self.new_max_found = False

                # write rx_dBm to heatmap
                self.heatmap.add_point(pos_x, pos_y, rx_dBm)
                # print(f"Pos x: {pos_x}, pos y: {pos_y}")

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

    def do_inward_spiral(self):
        """Do inward spiral from 12500,12500 to 0,0"""
        steps = range(24000, 0, -1000)
        # steps = [24000, 22000, 20000, 18000, 16000, 14000, 12000, 10000, 8000, 6000, 4000, 2000, 1000, 500, 250, 100]
        step_index = 0

        while True:
            step = steps[step_index]
            self.next_step(RIGHT, step)
            self.next_step(DOWN, step)
            step_index += 1
            if step_index >= len(steps):
                break  # stop loop if past last index

            step = steps[step_index]
            self.next_step(LEFT, step)
            self.next_step(UP, step)
            step_index += 1
            if step_index >= len(steps):
                break  # stop loop if past last index

    def do_spiral(self, step_size, stop_after=5, no_max_limit=5, rx_power_limit=-35):
        """Do spiral until at circle_limit"""
        step = 0
        not_found_count = 0
        circle_count = 0  #

        prev_max_point = self.max_point

        while circle_count < stop_after:
            step += step_size
            self.next_step(LEFT, step)
            self.next_step(UP, step)

            step += step_size
            self.next_step(RIGHT, step)
            self.next_step(DOWN, step)

            circle_count += 1
            # pos_x, pos_y, rx_dBm = self.max_point

            if prev_max_point == self.max_point:
                not_found_count += 1
            else:
                not_found_count = 0

            if not_found_count >= no_max_limit:  # if not found after 5 cycles break - TODO is this ok? - should w
                break

    def get_max_position(self):
        """Return position of maximum power and read power"""
        return self.max_point

    def move_to_position(self, pos_x, pos_y):
        """Move motor to selected position"""
        self.current_target_x = pos_x
        self.current_target_y = pos_y

        print(f"Moving to selected position: {self.current_target_x}, {self.current_target_y}")


        pos_x = 0
        pos_y = 0

        
        if self.remote:
            pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
            print(f"Remote motors position: {pos_x}, {pos_y}")
        else:
            pos_x, pos_y = self.client.get_motors_position()
            print(f"Local motors position: {pos_x}, {pos_y}")
        

        retry_count = 0
        prev_pos_x = pos_x
        prev_pos_y = pos_y

        while self.current_target_x != pos_x or self.current_target_y != pos_y:
            try:
                
                if self.remote:
                    self.client.issue_remote_command("move_motors_to", (self.current_target_x, self.current_target_y))
                    print(f"Remote moving motors: {pos_x}, {pos_y}")
                else:
                    self.client.move_motors_to(self.current_target_x, self.current_target_y)
                    print(f"Local moving motors: {pos_x}, {pos_y}")
                

                
                if self.remote:
                    print(f"Remote motors position: {pos_x}, {pos_y}")
                    pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
                else:
                    pos_x, pos_y = self.client.get_motors_position()
                    print(f"Local motors position: {pos_x}, {pos_y}")
                

                if pos_x == prev_pos_x and pos_y == prev_pos_y:
                    retry_count += 1

                if retry_count > 15:  # break after 15 seconds
                    break
            except Exception as e:
                log.error(e)
            time.sleep(1)  # sleep until motor moves to desired position

        print("END OF MOVE TO POSITION LOOP?")


    def move_to_max_position(self):
        """Move motor to maximum found position"""
        self.current_target_x = self.max_point["x"]
        self.current_target_y = self.max_point["y"]

        print(f"Moving to max: {self.current_target_x}, {self.current_target_y}")

        
        if self.remote:
            pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
        else:
            pos_x, pos_y = self.client.get_motors_position()
        

        while self.current_target_x != pos_x and self.current_target_y != pos_y:
            try:
                
                if self.remote:
                    self.client.issue_remote_command("move_motors_to", (self.current_target_x, self.current_target_y))
                else:
                    self.client.move_motors_to(self.current_target_x, self.current_target_y)
                
                
                
                if self.remote:
                    pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
                else:
                    pos_x, pos_y = self.client.get_motors_position()
                
            except Exception as e:
                log.error(e)
            time.sleep(1)  # sleep until motor moves to desired position

        self.new_max_found = False

    def move_to_start_position(self):
        """Move to start position"""
        self.current_target_x = self.start_pos_x
        self.current_target_y = self.start_pos_y

        print(f"Moving to start position: {self.current_target_x}, {self.current_target_y}")

        
        if self.remote:
            pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
        else:
            pos_x, pos_y = self.client.get_motors_position()
        

        while self.current_target_x != pos_x and self.current_target_y != pos_y:
            
            if self.remote:
                self.client.issue_remote_command("move_motors_to", (self.current_target_x, self.current_target_y))
            else:
                self.client.move_motors_to(self.current_target_x, self.current_target_y)
            
            
            if self.remote:
                pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
            else:
                pos_x, pos_y = self.client.get_motors_position()
            
            time.sleep(1)  # sleep until motor moves to desired position

        