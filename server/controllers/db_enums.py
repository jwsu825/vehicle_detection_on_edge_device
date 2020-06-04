import enum


class ServerCommandStatus(enum.Enum):
    received = 1
    sent = 2
    completed = 3
    errored = 4


class ServerCommands(enum.Enum):
    reboot = 1
    shutdown = 2
    change_filter = 3
    change_frame_rate = 4
