import xmlrpc.client
import time
import logging
from threading import Thread, Lock

from ...src.constants import ALIGNMENT_ENGINE_PORT
from ..src.alignment_engine import AlignmentEngine
"""
Base Align class used in alignment algorithms

Implements common methods used:
* update_unit_data - gathers data from both units in set interval
* move_to_position - move selected unit to specified position, arguments: *Primary/Secondary, *position X, *position Y
* move_to_max - move to currently saved max, arguments: *Primary/Secondary
* set_max_point_strategy - set max point selection strategy, arguments: *Function pointer

"""

log = logging.getLogger()

class Strategy():
    LOCAL_MAX = 1
    GLOBAL_MAX = 2
    MAX_SUM = 3

IP = "localhost"  # KORUZA IP or localhost - if running on local machine use KORUZA IP
RESEND_COMMAND_TIME = 2

class Align():
    def __init__(self):
        """Initialize base Align class"""
        self.lock = Lock()  # lock used in RPC synchronization
        self.running = None

        # keep track of maximum values in each iteration
        # one iteration is one spiral of either primary or secondary unit
        self.maximum = {
            "primary": {
                "x": 0,
                "y": 0,
                "dBm": -40
            },
            "secondary": {
                "x": 0,
                "y": 0,
                "dBm": -40
            }    
        }

        self.current_state = {
            "primary": {
                "x": 0,
                "y": 0,
                "dBm": -40
            },
            "secondary": {
                "x": 0,
                "y": 0,
                "dBm": -40
            }  
        }
        
        # NOTE: error handling of such instantiation has to be done by the user
        self.alignment_engine_proxy = xmlrpc.client.ServerProxy(f"http://{IP}:{ALIGNMENT_ENGINE_PORT}", allow_none=True)  # create client proxy to alignment engine
        try:
            self.primary, self.secondary = self.alignment_engine_proxy.initialize()
        except Exception as e:
            print(f"Failed to initialize connection to alignment engine: {e}")
            self.primary = None
            self.secodnary = None

        time.sleep(2)  # wait for client to init

        self.maximum_point_strategy = None
        self.maximum_dBm = -40  # global maximum of both units

        self.monitor_thread = None

    def __del__(self):
        """Destructor"""
        self.running = False
        self.monitor_thread.join()
        self.monitor_thread = None

    def reset_maximum(self, unit):
        """Reset both maxima"""
        self.maximum[unit]["x"] = 0
        self.maximum[unit]["y"] = 0
        self.maximum[unit]["dBm"] = -40

    def move_to_max(self, unit, rx_power_limit):
        """Move selected unit to max point"""
        print(f'====== MOVING TO MAX {self.maximum[unit]["x"]}, {self.maximum[unit]["y"]} ON {unit} ======')
        self.move_to_position(unit, self.maximum[unit]["x"], self.maximum[unit]["y"], rx_power_limit)

    def get_current_position(self, unit):
        """Get current position of unit"""
        self.lock.acquire()        
        current_x = self.current_state[unit]["x"]
        current_y = self.current_state[unit]["y"]
            # print(f"Local motors position: {current_x}, {current_y}")
        self.lock.release()

        return current_x, current_y

    def move_to_position(self, unit, target_x, target_y, rx_power_limit):
        """Move motor to selected position"""
        print(f"Moving to selected position: {target_x}, {target_y}")

        current_x, current_y = self.get_current_position(unit)

        retry_count = 0
        prev_pos_x = current_x
        prev_pos_y = current_y

        command_time = 0

        while current_x != target_x or current_y != target_y:
            
            current_x, current_y = self.get_current_position(unit)

            # break out if above desired rx power
            current_rx_power = self.current_state[unit]["dBm"]
            if current_rx_power > rx_power_limit:
                # when breaking out make sure to stay at current position
                try:
                    self.lock.acquire()
                    self.alignment_engine_proxy.move_motor(unit, target_x, target_y)
                    command_time = time.time()
                    self.lock.release()
                except Exception as e:
                    self.lock.release()
                    log.error(e)
                return

            if target_x == -3750:  # NOTE HARDWARE BUG ON BOTH UNITS at -3750 motor gets stuckt at ~-3550
                target_x = -4000

            if time.time() - command_time > RESEND_COMMAND_TIME:
                try:
                    self.lock.acquire()
                    self.alignment_engine_proxy.move_motor(unit, target_x, target_y)
                    command_time = time.time()
                    self.lock.release()
                except Exception as e:
                    self.lock.release()
                    log.error(e)

            if current_x == prev_pos_x and current_y == prev_pos_y:
                retry_count += 1
            else:
                retry_count = 0

            if retry_count > 30:  # break after 60 seconds
                print("TIMEOUT ON MOTOR MOVEMENT")
                break

            prev_pos_x = current_x
            prev_pos_y = current_y

            time.sleep(0.5)  # sleep until motor moves to desired position

        # print("END OF MOVE TO POSITION LOOP?")

    def set_max_point_strategy(self, strategy):
        """Set desired max point selection strategy"""
        if strategy == Strategy.LOCAL_MAX:
            self.maximum_point_strategy = self._strategy_local_maxima
        if strategy == Strategy.GLOBAL_MAX:
            self.maximum_point_strategy = self._strategy_global_maximum
        if strategy == Strategy.MAX_SUM:
            self.maximum_point_strategy = self._strategy_maximum_sum

    def start_monitoring(self):
        """Start monitoring thread"""
        self.running = True
        self.monitor_thread = Thread(target=self._get_unit_diagnostics, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.running = None

    # TODO move to separate class
    def _strategy_local_maxima(self):
        """Update the maximum position on each unit, regardless of the position of the other unit"""

        if self.current_state[self.primary]["dBm"] > self.maximum[self.primary]["dBm"]:
            self.maximum[self.primary] = self.current_state[self.primary].copy()
            print(f'New max point on primary unit: {self.maximum[self.primary]}')

        if self.current_state[self.secondary]["dBm"] > self.maximum[self.secondary]["dBm"]:
            self.maximum[self.secondary] = self.current_state[self.secondary].copy()
            print(f'New max point on secondary unit: {self.maximum[self.secondary]}')

    def _strategy_global_maximum(self):
        """Update position of maxima on both units if a global maximum is found"""
        if self.current_state[self.secondary]["dBm"] > self.maximum_dBm or self.current_state[self.primary]["dBm"] > self.maximum_dBm:

            self.maximum[self.secondary] = self.current_state[self.secondary].copy()
            print(f'New max point on secondary unit: {self.maximum[self.secondary]}')

            self.maximum[self.primary] = self.current_state[self.primary].copy()
            print(f'New max point on primary unit: {self.maximum[self.primary]}')

            self.maximum_dBm = self.maximum[self.primary]["dBm"].copy() if self.maximum[self.primary]["dBm"] > self.maximum[self.secondary]["dBm"] else self.maximum[self.secondary]["dBm"].copy()
            print(f"New total max dBm: {self.maximum_dBm}")

    def _strategy_maximum_sum(self):
        """Update position of maxima on both units when sum of signal strength is at new maximum"""

        # update max points if total dBm is higher than previously
        if self.current_state[self.primary]["dBm"] + self.current_state[self.secondary]["dBm"] > self.maximum[self.primary]["dBm"] + self.maximum[self.secondary]["dBm"]:
            self.maximum[self.secondary] = self.current_state[self.secondary].copy()
            print(f'New max point on secondary unit: {self.maximum[self.secondary]}')

            self.maximum[self.primary] = self.current_state[self.primary].copy()
            print(f'New max point on primary unit: {self.maximum[self.primary]}')
  
    def _update_max_points(self):
        """Call set function to update max points"""
        self.maximum_point_strategy()

    def _get_unit_diagnostics(self):
        """Get both unit diagnostics in a short interval"""

        while True:
            if self.running:
                try:
                    for unit in (self.primary, self.secondary):
                        self.lock.acquire()
                        self.current_state[unit]["x"], self.current_state[unit]["y"] = self.alignment_engine_proxy.read_motor_position(unit)
                        self.lock.release()

                        self.lock.acquire()
                        self.current_state[unit]["dBm"] = self.alignment_engine_proxy.read_sfp_data(unit).get("sfp_0", {}).get("diagnostics", {}).get("rx_power_dBm", -40)
                        self.lock.release()

                    self._update_max_points()
                    
                except Exception as e:
                    self.lock.release()
                    log.error(f"Error getting rx_dBm: {e}")            

                time.sleep(0.2)

            elif self.running == False:
                break
            
            elif self.running is None:
                pass
