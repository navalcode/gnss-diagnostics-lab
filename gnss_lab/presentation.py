"""Plain-text diagnostics for people; the JSON report remains the data contract."""


def render_text(result, language='en'):
    es = language == 'es'

    def metric(value, unit='', decimals=None):
        if value is None:
            return 'Sin datos' if es else 'No data'
        number = f'{value:.{decimals}f}' if decimals is not None else str(value)
        return f'{number} {unit}'.rstrip()

    def row(en, spanish, value):
        return f'  {spanish if es else en}: {value}'

    first = result['time_to_first_fix_ms']
    first_text = metric(first, 'ms') if first is not None else ('Sin fix' if es else 'No fix')
    lines = [
        ('Diagnóstico sintético' if es else 'Synthetic diagnostics') + f' · {result["backend"]}',
        '', 'Captura' if es else 'Capture',
        row('Samples', 'Muestras', result['sample_count']),
        row('Valid fixes', 'Fixes válidos', result['fix_count']),
        row('No fix', 'Sin fix', result['no_fix_count']),
        row('Time to first fix', 'Tiempo hasta primer fix', first_text),
        '', 'Continuidad' if es else 'Continuity',
        row('Gaps', 'Huecos', f'{result["gap_count"]} (> {result["gap_threshold_ms"]} ms)'),
        row('Longest fix interval', 'Mayor intervalo entre fixes', metric(result['largest_fix_interval_ms'], 'ms')),
        row('Trailing time without fix', 'Tiempo final sin fix', metric(result['tail_without_fix_ms'], 'ms')),
        row('Apparent jumps', 'Saltos aparentes', f'{result["apparent_speed_jump_count"]} (> {result["jump_threshold_mps"]:g} m/s)'),
        '', 'Comparación con la referencia' if es else 'Comparison with supplied reference',
        row('Matched fixes', 'Fixes emparejados', result['matched_fix_count']),
        row('Unmatched fixes', 'Fixes sin pareja', result['unmatched_fix_count']),
    ]
    for key, label in [('mean', 'Mean error' if not es else 'Error medio'), ('p50', 'p50'), ('p95', 'p95'), ('rmse', 'RMSE')]:
        lines.append(f'  {label}: {metric(result["error_m"][key], "m", 2)}')
    lines += [
        row('Mean reported uncertainty', 'Incertidumbre declarada media', metric(result['mean_reported_accuracy_m'], 'm', 2)),
        '', 'Modelo: esfera de 6371000 m; emparejado por tiempo exacto.' if es else 'Model: 6371000 m sphere; exact elapsed-time pairing.',
        'No acredita precisión física. Exit 0 indica procesamiento correcto.' if es else 'Does not establish physical accuracy. Exit 0 means processing succeeded.',
    ]
    return '\n'.join(lines)
