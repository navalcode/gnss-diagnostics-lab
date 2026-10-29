import argparse
import json
from pathlib import Path
import sys
from .capture import read_capture
from .diagnostics import analyze
from .distance import NativeDistance, distance_m


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local diagnostics; no device acquisition or network access.')
    parser.add_argument('--samples', type=Path, default=Path('examples/observed.csv'))
    parser.add_argument('--reference', type=Path, default=Path('examples/reference.csv'))
    parser.add_argument('--backend', choices=['python', 'native'], default='python')
    parser.add_argument('--format', choices=['json', 'text'], default='json')
    parser.add_argument('--language', choices=['en', 'es'], default='en')
    parser.add_argument('--max-gap-ms', type=int, default=2500)
    parser.add_argument('--jump-mps', type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        distance = NativeDistance() if args.backend == 'native' else distance_m
        result = analyze(read_capture(args.samples), read_capture(args.reference), max_gap_ms=args.max_gap_ms, jump_mps=args.jump_mps, distance=distance)
    except (ValueError, OSError, TypeError) as error:
        # Avoid echoing file paths/content or dynamic library loader details.
        message = str(error) if isinstance(error, ValueError) else 'cannot read capture or load project native library'
        print(('Error: ' if args.language == 'es' else 'Error: ') + message, file=sys.stderr)
        return 2
    result['backend'] = args.backend
    if args.format == 'json':
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        labels = ('Diagnóstico sintético', 'Fixes válidos', 'Sin fix', 'Tiempo hasta primer fix', 'Huecos', 'Saltos aparentes', 'No acredita precisión física') if args.language == 'es' else ('Synthetic diagnostics', 'Valid fixes', 'No fix', 'Time to first fix', 'Gaps', 'Apparent jumps', 'Does not establish physical accuracy')
        first = result['time_to_first_fix_ms']
        first_text = f'{first} ms' if first is not None else ('Sin fix' if args.language == 'es' else 'No fix')
        print(f'{labels[0]} · {args.backend}\n{labels[1]}: {result["fix_count"]}\n{labels[2]}: {result["no_fix_count"]}\n{labels[3]}: {first_text}\n{labels[4]}: {result["gap_count"]}\n{labels[5]}: {result["apparent_speed_jump_count"]}\n{labels[6]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
