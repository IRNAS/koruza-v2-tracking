
import time
import logging

log = logging.getLogger()

range_x = 14000
range_y = 14000

LEFT = {"name": "left", "direction": "-1"}
RIGHT = {"name": "right", "direction": "1"}
DOWN = {"name": "down", "direction": "-1"}
UP = {"name": "up", "direction": "1"}

IMG_FOLDER = "/home/pi/koruza_v2/koruza_v2_tracking/images/"

class CrossScan():
    def __init__(self, client, start_pos_x=None, start_pos_y=None, remote=None, lock=None):
        """Initialize spiral scan class"""
        # initialize rpc client
        # self.client = xmlrpc.client.ServerProxy(f"http://localhost:{KORUZA_MAIN_PORT}", allow_none=True)

        self.lock = lock

        self.client = client
        self.remote = remote

        self.current_target_x = None
        self.current_target_y = None

        self.start_pos_x = start_pos_x
        self.start_pos_y = start_pos_y

    def scan_window(self, max_offset, vertical_step):
        """Scan window with scanlines moving from top to bottom"""

        vertical_offset = max_offset

        self.move_to_position(-max_offset, vertical_offset)  # upper left corner

        # do until bottom corner is reached
        while self.current_target_y >= -max_offset:

            # move down and rigth
            self.move_to_position(max_offset, vertical_offset)
            vertical_offset -= vertical_step

            # move down and left
            self.move_to_position(-max_offset, vertical_offset)
            vertical_offset -= vertical_step

    def move(self, direction_enum, step):
        """Move in horizontal/vertical direction"""

        # get current position
        self.lock.acquire()
        if self.remote:
            self.current_target_x, self.current_target_y = self.client.issue_remote_command("get_motors_position", ())
        else:
            self.current_target_x, self.current_target_y = self.client.get_motors_position()
        self.lock.release()

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
            self.lock.acquire()
            if self.remote:
                self.client.issue_remote_command("move_motors_to", (self.current_target_x, self.current_target_y))
            else:
                self.client.move_motors_to(self.current_target_x, self.current_target_y)  
            self.lock.release()

            start_time = time.time()
            count_not_changed = 0  # if read values does not change for x reads break out of loop
            prev_pos_x = None
            prev_pos_y = None
            pos_x = None
            pos_y = None
                
            # wait for motors to move
            for _ in range(0, 1000):  # wait for motors to move to position - TODO find actual time range
                # TODO implement stuck check
                # print(f"Current target x: {self.current_target_x}, {self.current_target_y}")
                try:
                    self.lock.acquire()
                    if self.remote:
                        pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
                    else:
                        pos_x, pos_y = self.client.get_motors_position()
                    self.lock.release()

                    # print(f"Read pos x: {pos_x}, pos y: {pos_y}")
                except Exception as e:
                    self.lock.release()
                    log.error(f"An error occured when unpacking motor position values: {e}")

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

    def do_cross(self, step_size):
        """Do spiral until at circle_limit"""
        self.move(LEFT, step_size)
        self.move(RIGHT, 2 * step_size)  # move back and right
        self.move(LEFT, step_size)  # move back to start position

        self.move(DOWN, step_size)
        self.move(UP, 2 * step_size)
        self.move(DOWN, step_size)  # move back to start position

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

        self.lock.acquire()        
        if self.remote:
            pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
            print(f"Remote motors position: {pos_x}, {pos_y}")
        else:
            pos_x, pos_y = self.client.get_motors_position()
            print(f"Local motors position: {pos_x}, {pos_y}")
        self.lock.release()

        retry_count = 0
        prev_pos_x = pos_x
        prev_pos_y = pos_y

        while self.current_target_x != pos_x or self.current_target_y != pos_y:
            try:
                self.lock.acquire()
                if self.remote:
                    self.client.issue_remote_command("move_motors_to", (self.current_target_x, self.current_target_y))
                    print(f"Remote moving motors: {pos_x}, {pos_y}")
                else:
                    self.client.move_motors_to(self.current_target_x, self.current_target_y)
                    print(f"Local moving motors: {pos_x}, {pos_y}")
                self.lock.release()

                self.lock.acquire()
                if self.remote:
                    print(f"Remote motors position: {pos_x}, {pos_y}")
                    pos_x, pos_y = self.client.issue_remote_command("get_motors_position", ())
                else:
                    pos_x, pos_y = self.client.get_motors_position()
                    print(f"Local motors position: {pos_x}, {pos_y}")
                self.lock.release()

                if pos_x == prev_pos_x and pos_y == prev_pos_y:
                    retry_count += 1

                if retry_count > 15:  # break after 15 seconds
                    break
            except Exception as e:
                self.lock.release()
                log.error(e)

            time.sleep(1)  # sleep until motor moves to desired position

        print("END OF MOVE TO POSITION LOOP?")