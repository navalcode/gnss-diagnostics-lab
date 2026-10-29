import math
import statistics
from .capture import Sample
from .distance import distance_m


def analyze(samples: list[Sample], reference: list[Sample], *, max_gap_ms=2500, jump_mps=10.0, distance=distance_m):
    if not samples or not reference:
        raise ValueError('both captures need samples')
    if isinstance(max_gap_ms, bool) or not isinstance(max_gap_ms, int) or max_gap_ms < 1:
        raise ValueError('max_gap_ms must be a positive integer')
    try:
        valid_jump = type(jump_mps) in (float, int) and math.isfinite(jump_mps) and jump_mps > 0
    except OverflowError:
        valid_jump = False
    if not valid_jump:
        raise ValueError('jump_mps must be finite and positive')
    # The CLI parser guarantees schema/order. Keep direct API use explicit as well.
    for capture in (samples, reference):
        previous = -1
        for sample in capture:
            if not isinstance(sample.elapsed_ms, int) or isinstance(sample.elapsed_ms, bool) or sample.elapsed_ms <= previous:
                raise ValueError('timestamps must be nonnegative and strictly increasing')
            previous = sample.elapsed_ms
            if sample.has_fix:
                distance(sample.latitude_deg, sample.longitude_deg, sample.latitude_deg, sample.longitude_deg)
                if sample.horizontal_accuracy_m is None or not math.isfinite(sample.horizontal_accuracy_m) or sample.horizontal_accuracy_m < 0:
                    raise ValueError('invalid reported accuracy')
            elif sample.longitude_deg is not None or sample.horizontal_accuracy_m is not None:
                raise ValueError('partial no-fix sample')
    truth = {sample.elapsed_ms: sample for sample in reference if sample.has_fix}
    fixes = [sample for sample in samples if sample.has_fix]
    errors, speeds, intervals = [], [], []
    for index, sample in enumerate(fixes):
        expected = truth.get(sample.elapsed_ms)
        if expected is not None:
            errors.append(distance(sample.latitude_deg, sample.longitude_deg, expected.latitude_deg, expected.longitude_deg))
        if index:
            before = fixes[index - 1]
            elapsed = sample.elapsed_ms - before.elapsed_ms
            intervals.append(elapsed)
            speeds.append(distance(before.latitude_deg, before.longitude_deg, sample.latitude_deg, sample.longitude_deg) / (elapsed / 1000))
    errors.sort()
    return {
        'model': {'kind': 'sphere', 'radius_m': 6371000.0, 'pairing': 'exact elapsed_ms', 'p95': 'nearest rank'},
        'sample_count': len(samples), 'fix_count': len(fixes), 'no_fix_count': len(samples) - len(fixes),
        'capture_end_ms': samples[-1].elapsed_ms,
        'time_to_first_fix_ms': fixes[0].elapsed_ms if fixes else None,
        'tail_without_fix_ms': samples[-1].elapsed_ms - fixes[-1].elapsed_ms if fixes else samples[-1].elapsed_ms,
        'largest_fix_interval_ms': max(intervals, default=None),
        'gap_count': sum(value > max_gap_ms for value in intervals),
        'gap_threshold_ms': max_gap_ms,
        'apparent_speed_jump_count': sum(value > jump_mps for value in speeds),
        'jump_threshold_mps': jump_mps,
        'matched_fix_count': len(errors), 'unmatched_fix_count': len(fixes) - len(errors),
        'error_m': {
            'mean': statistics.fmean(errors) if errors else None,
            'p50': statistics.median(errors) if errors else None,
            'p95': errors[math.ceil(.95 * len(errors)) - 1] if errors else None,
            'rmse': math.sqrt(statistics.fmean(value * value for value in errors)) if errors else None,
        },
        'mean_reported_accuracy_m': statistics.fmean(s.horizontal_accuracy_m for s in fixes) if fixes else None,
        'interpretation': 'Diagnostic against supplied reference; not physical accuracy or receiver certification.',
    }
