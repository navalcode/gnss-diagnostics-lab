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
    first_text = metric(first, 'ms') if first is not None else ('Sin posición' if es else 'No fix')
    lines = [
        ('Informe de captura GNSS' if es else 'GNSS capture report') + f' · {result["backend"]}',
        '', 'Captura' if es else 'Capture',
        row('Samples', 'Muestras', result['sample_count']),
        row('Samples with a fix', 'Muestras con posición', result['fix_count']),
        row('Samples without a fix', 'Muestras sin posición', result['no_fix_count']),
        row('Time to first fix', 'Tiempo hasta la primera posición', first_text),
        '', 'Continuidad' if es else 'Continuity',
        row('Gaps', 'Huecos', f'{result["gap_count"]} (> {result["gap_threshold_ms"]} ms)'),
        row('Longest fix interval', 'Mayor intervalo entre posiciones', metric(result['largest_fix_interval_ms'], 'ms')),
        row('Trailing time without fix', 'Tiempo final sin posición', metric(result['tail_without_fix_ms'], 'ms')),
        row('Apparent jumps', 'Saltos aparentes', f'{result["apparent_speed_jump_count"]} (> {result["jump_threshold_mps"]:g} m/s)'),
        '', 'Comparación con la referencia' if es else 'Comparison with supplied reference',
        row('Matched fixes', 'Posiciones emparejadas', result['matched_fix_count']),
        row('Unmatched fixes', 'Posiciones sin referencia', result['unmatched_fix_count']),
    ]
    for key, label in [('mean', 'Mean error' if not es else 'Error medio'), ('p50', 'p50'), ('p95', 'p95'), ('rmse', 'RMSE')]:
        lines.append(f'  {label}: {metric(result["error_m"][key], "m", 2)}')
    lines += [
        row('Mean reported uncertainty', 'Incertidumbre media declarada', metric(result['mean_reported_accuracy_m'], 'm', 2)),
        '', 'Modelo: radio esférico de 6 371 000 m; se emparejan tiempos idénticos.' if es else 'Model: sphere radius 6,371,000 m; identical elapsed times are paired.',
        'Las cifras describen las muestras suministradas; no validan un receptor.' if es else 'These figures describe the supplied samples; they do not validate a receiver.',
    ]
    return '\n'.join(lines)


ERROR_GUIDANCE = {
    'capture is empty': (
        'The capture has no samples. Add at least one data row after the header.',
        'La captura no contiene muestras. Añade al menos una fila de datos después de la cabecera.'),
    'unexpected CSV header': (
        'Use this exact header: elapsed_ms,fix,latitude_deg,longitude_deg,horizontal_accuracy_m',
        'Usa esta cabecera exacta: elapsed_ms,fix,latitude_deg,longitude_deg,horizontal_accuracy_m'),
    'capture must be UTF-8': ('Save the CSV as UTF-8.', 'Guarda el CSV en UTF-8.'),
    'capture exceeds 1 MiB': ('Split the capture into files of at most 1 MiB.', 'Divide la captura en archivos de hasta 1 MiB.'),
    'capture exceeds 10000 samples': ('Use at most 10,000 samples per capture.', 'Usa un máximo de 10 000 muestras por captura.'),
    'timestamps must strictly increase': ('Use increasing elapsed_ms values without duplicates.', 'Usa valores elapsed_ms crecientes y sin duplicados.'),
    'invalid elapsed_ms': ('Set elapsed_ms to a nonnegative integer below 10^15.', 'Usa un entero elapsed_ms no negativo e inferior a 10^15.'),
    'unexpected column count': ('Give every row the same five columns as the header.', 'Incluye en cada fila las mismas cinco columnas que en la cabecera.'),
    'no-fix row must have empty position fields': ('For fix=0, leave the three position fields empty.', 'Con fix=0, deja vacíos los tres campos de posición.'),
    'fix must be 0 or 1': ('Set fix to 0 or 1.', 'El campo fix debe ser 0 o 1.'),
    'invalid position number': ('Use numeric coordinates and uncertainty for fix=1.', 'Con fix=1, usa números para coordenadas e incertidumbre.'),
    'position outside contract': ('Use finite latitude -90..90, longitude -180..180 and uncertainty 0..1000000 m.', 'Usa latitud finita de -90 a 90, longitud de -180 a 180 e incertidumbre de 0 a 1 000 000 m.'),
    'max_gap_ms must be a positive integer': ('Set --max-gap-ms to a positive integer.', 'Indica un entero positivo en --max-gap-ms.'),
    'jump_mps must be finite and positive': ('Set --jump-mps to a finite positive number.', 'Indica un número finito y positivo en --jump-mps.'),
    'malformed CSV': ('Check CSV delimiters and matching quotes.', 'Revisa los separadores CSV y el cierre de comillas.'),
    'malformed CSV header': ('Check the header’s delimiters and matching quotes.', 'Revisa los separadores y el cierre de comillas de la cabecera.'),
    'native distance failed its result contract': ('Rebuild the project library or select --backend python; the native result was invalid.', 'Recompila la biblioteca del proyecto o selecciona --backend python; el resultado nativo no es válido.'),
    'capture_unreadable': ('Check that --samples and --reference point to readable CSV files.', 'Comprueba que --samples y --reference indiquen archivos CSV que puedas leer.'),
    'native_unavailable': ('Run python3 tools/build_native.py, or select --backend python.', 'Ejecuta python3 tools/build_native.py o selecciona --backend python.'),
}


def render_error(message, language='en'):
    # Parser diagnostics contain only contract labels and numeric row indices.
    # Unknown low-level messages are not echoed (paths/loader details stay private).
    import re
    match = re.fullmatch(r'row (\d+): (.+)', message)
    detail = match[2] if match else message
    pair = ERROR_GUIDANCE.get(detail)
    if pair is None:
        pair = ('Check the CSV schema and numeric ranges, then try again.',
                'Revisa el esquema CSV y los rangos numéricos y vuelve a intentarlo.')
    row = (('Fila ' if language == 'es' else 'Row ') + match[1] + ': ') if match else ''
    return 'Error: ' + row + pair[language == 'es']
