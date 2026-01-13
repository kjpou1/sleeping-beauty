from enum import Enum


class SleepStage(str, Enum):
    AWAKE = "awake"
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"
