import serial

class VelmexStage:
    # Stage is XN10-0060-M01-71 -> 6" travel distance, 1mm per turn
    adv_per_turn = 1.00 # mm
    steps_per_turn = 400 # number of motor steps to make 1 full turn

    @staticmethod
    def mm_to_steps(mm):
        return mm * VelmexStage.adv_per_turn * VelmexStage.steps_per_turn

    def query(self, cmd_str, wait = True):
        written = self.dev.write(cmd_str.encode('ascii'))
        print(f'Write {cmd_str}: {written} bytes sent')

        read_str = ''
        while wait:
            read_str += self.dev.read().decode('ascii')
            # caret indicates end of response
            if read_str[-1] == '^': break

        print(f'Read back: \'{read_str}\'')
        return read_str

    def home(self):
        return self.query('C, E I1M-0, R') # go to negative limit

    def incr(self, mm):
        # increment the current position
        steps = round(self.mm_to_steps(mm))
        return self.query(f'C, E I1M{steps}, R')

    def move(self, mm):
        # move to a position relative to the zero'ed position
        steps = round(self.mm_to_steps(mm))
        return self.query(f'C, E IA1M{steps}, R')

    def zero(self):
        return self.query('C, E IA1M-0, R')

    def __init__(self, device_file = '/dev/ttyUSB0'):
        # total travel distance is 152mm @ 5mm/sec -> ~30s timeout
        self.dev = serial.Serial(device_file, timeout = 35.0)
        self.query('C, E S1M2000, R') # set speed to 5mm / sec
        self.home()
        self.zero()
