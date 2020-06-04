# ***********************************************
# ++        KEEP ALL CONSTANTS HERE            ++
# ***********************************************


class Status:
    ERRORED = 0
    NOT_STARTED = 1
    RUNNING = 2
    COMPLETE = 3
    WAITING = 4
    STOPPED = 5


# ---- IMG ACQUISITION ----
RAMP_IMAGES = 30  # number of frames to calibrate settings
TMP_DIRECTORY = '/var/tmp/image/'

# ---- CONFIGURATION CONSTANTS ----
DEFAULT_CONFIG_FILE = './configuration/config.ini'
