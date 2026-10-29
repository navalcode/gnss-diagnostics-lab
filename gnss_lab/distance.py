"""A spherical model, deliberately not an ellipsoidal geodetic solution."""
import ctypes
import math
from pathlib import Path
import sys

RADIUS_M = 6_371_000.0


def validate_coordinates(lat_a, lon_a, lat_b, lon_b):
    if any(type(v) not in (float, int) for v in (lat_a, lon_a, lat_b, lon_b)):
        raise ValueError('coordinates must be numbers')
    if not (-90 <= lat_a <= 90 and -90 <= lat_b <= 90 and -180 <= lon_a <= 180 and -180 <= lon_b <= 180):
        raise ValueError('coordinates outside contract')


def distance_m(lat_a, lon_a, lat_b, lon_b):
    validate_coordinates(lat_a, lon_a, lat_b, lon_b)
    a, b = math.radians(lat_a), math.radians(lat_b)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(lon_b - lon_a) / 2) ** 2
    return 2 * RADIUS_M * math.asin(math.sqrt(min(1.0, max(0.0, h))))


class NativeDistance:
    """Loads only the project's explicitly built library, never capture-supplied paths."""
    def __init__(self):
        extension = 'dylib' if sys.platform == 'darwin' else 'so'
        path = Path(__file__).resolve().parents[1] / 'build' / f'libgnss_distance.{extension}'
        self.library = ctypes.CDLL(str(path))
        self.function = self.library.gnss_distance_deg
        self.function.argtypes = [ctypes.c_double] * 4 + [ctypes.POINTER(ctypes.c_double)]
        self.function.restype = ctypes.c_int

    def __call__(self, lat_a, lon_a, lat_b, lon_b):
        validate_coordinates(lat_a, lon_a, lat_b, lon_b)
        result = ctypes.c_double()
        status = self.function(lat_a, lon_a, lat_b, lon_b, ctypes.byref(result))
        if status != 0 or not math.isfinite(result.value) or result.value < 0:
            raise ValueError('native distance failed its result contract')
        return result.value
