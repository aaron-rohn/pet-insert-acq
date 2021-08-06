import time
from system import System
from stage_control import StageController

with System(['192.168.1.100'], [2]) as sys:

    controller = StageController()

    sys.set_all_dac(False, 0.030)
    sys.set_all_dac(True, 29.5)

    for i in range(8):
        deg = 360.0/16 * i
        ustep = round(StageController.deg_to_ustep(deg))
        print('%f %d' % (deg, ustep))
        controller.send("move abs %s" % str(ustep))

        sys.start_acq('temperature_6v_position_' + str(i) + '_')
        time.sleep(300)
        sys.stop_acq()

    sys.set_all_dac(True, 0)
    controller.send("move abs 0")
