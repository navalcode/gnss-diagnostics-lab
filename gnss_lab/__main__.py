import argparse
import json
from pathlib import Path
import sys
from .capture import read_capture
from .diagnostics import analyze
from .distance import NativeDistance, distance_m
from .presentation import render_text, render_error


def main(argv=None):
    parser = argparse.ArgumentParser(description='Analyze sample and reference CSV files using exact elapsed-time matching.')
    parser.add_argument('--samples', type=Path, default=Path('examples/observed.csv'), help='Observed CSV; default: bundled synthetic capture')
    parser.add_argument('--reference', type=Path, default=Path('examples/reference.csv'), help='Reference CSV using the same schema and session clock')
    parser.add_argument('--backend', choices=['python', 'native'], default='python', help='Native requires tools/build_native.py; default: python')
    parser.add_argument('--format', choices=['json', 'text'], default='json', help='JSON for tools, text for review; default: json')
    parser.add_argument('--language', choices=['en', 'es'], default='en', help='Report and recovery-message language; CSV field names stay unchanged')
    parser.add_argument('--max-gap-ms', type=int, default=2500, help='Count fix intervals strictly above this value; default: 2500 ms')
    parser.add_argument('--jump-mps', type=float, default=10.0, help='Count apparent speeds strictly above this value; default: 10 m/s')
    args = parser.parse_args(argv)
    try:
        distance = NativeDistance() if args.backend == 'native' else distance_m
    except (ValueError, OSError, TypeError):
        print(render_error('native_unavailable', args.language), file=sys.stderr)
        return 2
    try:
        result = analyze(read_capture(args.samples), read_capture(args.reference), max_gap_ms=args.max_gap_ms, jump_mps=args.jump_mps, distance=distance)
    except (ValueError, OSError, TypeError) as error:
        message = str(error) if isinstance(error, ValueError) else 'capture_unreadable'
        print(render_error(message, args.language), file=sys.stderr)
        return 2
    result['backend'] = args.backend
    if args.format == 'json':
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        print(render_text(result, args.language))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
