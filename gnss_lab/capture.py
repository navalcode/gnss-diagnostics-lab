from dataclasses import dataclass
import csv
import io
import math
from pathlib import Path

HEADER = ['elapsed_ms', 'fix', 'latitude_deg', 'longitude_deg', 'horizontal_accuracy_m']
MAX_BYTES = 1_048_576
MAX_ROWS = 10_000


@dataclass(frozen=True)
class Sample:
    elapsed_ms: int
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    horizontal_accuracy_m: float | None = None

    def __post_init__(self):
        if type(self.elapsed_ms) is not int or not 0 <= self.elapsed_ms < 10**15:
            raise ValueError('invalid elapsed_ms')
        if self.latitude_deg is None:
            if self.longitude_deg is not None or self.horizontal_accuracy_m is not None:
                raise ValueError('partial no-fix sample')
        else:
            values = (self.latitude_deg, self.longitude_deg, self.horizontal_accuracy_m)
            if any(type(value) not in (float, int) for value in values):
                raise ValueError('position fields must be numbers')
            if not -90 <= self.latitude_deg <= 90 or not -180 <= self.longitude_deg <= 180 or not 0 <= self.horizontal_accuracy_m <= 1_000_000:
                raise ValueError('position outside contract')

    @property
    def has_fix(self):
        return self.latitude_deg is not None


def read_capture(path: Path) -> list[Sample]:
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('capture exceeds 1 MiB')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('capture must be UTF-8') from None
    reader = csv.DictReader(io.StringIO(text), strict=True)
    try:
        fieldnames = reader.fieldnames
    except csv.Error:
        raise ValueError('malformed CSV header') from None
    if fieldnames != HEADER:
        raise ValueError('unexpected CSV header')
    samples = []
    try:
        for index, row in enumerate(reader, 1):
            if index > MAX_ROWS:
                raise ValueError('capture exceeds 10000 samples')
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'row {index}: unexpected column count')
            elapsed = row['elapsed_ms']
            if not elapsed.isascii() or not elapsed.isdigit() or len(elapsed) > 15:
                raise ValueError(f'row {index}: invalid elapsed_ms')
            elapsed = int(elapsed)
            if samples and elapsed <= samples[-1].elapsed_ms:
                raise ValueError(f'row {index}: timestamps must strictly increase')
            if row['fix'] == '0':
                if any(row[key] for key in HEADER[2:]):
                    raise ValueError(f'row {index}: no-fix row must have empty position fields')
                sample = Sample(elapsed)
            elif row['fix'] == '1':
                try:
                    lat, lon, accuracy = (float(row[key]) for key in HEADER[2:])
                except ValueError:
                    raise ValueError(f'row {index}: invalid position number') from None
                if not all(math.isfinite(v) for v in (lat, lon, accuracy)) or not -90 <= lat <= 90 or not -180 <= lon <= 180 or not 0 <= accuracy <= 1_000_000:
                    raise ValueError(f'row {index}: position outside contract')
                sample = Sample(elapsed, lat, lon, accuracy)
            else:
                raise ValueError(f'row {index}: fix must be 0 or 1')
            samples.append(sample)
    except csv.Error:
        raise ValueError('malformed CSV') from None
    if not samples:
        raise ValueError('capture is empty')
    return samples
