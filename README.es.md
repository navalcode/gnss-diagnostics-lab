# GNSS Diagnostics Lab

[English](README.md)

Diagnóstico local original sobre **capturas CSV sintéticas**, con Python y un pequeño kernel C integrado mediante `ctypes`. Permite observar tiempo hasta primer fix, ausencia de fix, huecos, saltos aparentes y error frente a una referencia suministrada explícitamente.

El ejemplo incluye adquisición tardía, pérdida de fix y un valor atípico deliberados. Demuestra diagnósticos y una frontera nativa; no mide un receptor ni recoge ubicación del dispositivo.

## Ejecutar

Python 3.11 o superior, sin paquetes externos. El backend nativo requiere `cc` en macOS/Linux.

```sh
python3 -m gnss_lab
python3 -m gnss_lab --format text --language es
python3 tools/build_native.py
python3 -m gnss_lab --backend native
python3 -m unittest discover -s tests -v
```

Ejecutar desde la raíz. Los tests necesitan compilar C y fallan si falta la biblioteca; no omiten silenciosamente esa evidencia. El script solo compila `native/distance.c`; no se distribuyen binarios. El backend Python funciona sin compilador.

Resultado esperado: **3 fixes, 4 muestras sin fix, primer fix a 2000ms, un intervalo superior a 2500ms y un salto aparente superior a 10m/s**. El p95 frente a la referencia es aproximadamente 104,52m y la incertidumbre declarada es 3 m. La discrepancia es intencional; no certifica precisión real.

Salir con código 0 significa procesamiento correcto, incluso si las métricas son malas. Una entrada inválida o backend nativo no disponible devuelve 2, sin JSON. No se produce una certificación de calidad.

## Contrato de entrada

```csv
elapsed_ms,fix,latitude_deg,longitude_deg,horizontal_accuracy_m
0,0,,,
2000,1,0,0.00003,3
```

Cabecera exacta y ordenada; UTF-8 con BOM opcional; máximo 1 MiB y 10.000 muestras. Tiempo entero desde el inicio declarado en 0, entre 0 y 10¹⁵ exclusivo, estrictamente creciente. Fix es 0 o 1. Sin fix, los tres campos de posición deben estar vacíos. Con fix, latitud finita entre −90 y 90, longitud entre −180 y 180 e incertidumbre entre 0 y 1.000.000 m. El límite superior pertenece a este parser, no a una especificación de receptor.

Columnas ausentes o adicionales, duplicados, regresiones, números no finitos y fixes parciales fallan. Los ejemplos son recorridos matemáticos inventados cerca de (0,0), no trazas de personas ni ground truth real.

`--samples archivo.csv --reference referencia.csv` selecciona archivos locales. El programa solo los lee, imprime en stdout y no hace peticiones de red. La referencia usa el mismo esquema. Solo empareja timestamps exactos con fix en ambas capturas; no interpola ni alinea relojes automáticamente.

## Interpretar el reporte

- TTFF es el primer tiempo válido desde el cero declarado; no es un benchmark de adquisición física.
- Los huecos son intervalos entre fixes válidos consecutivos estrictamente superiores a `--max-gap-ms`. La cola sin fix se informa aparte. Sin fix, TTFF es nulo, nunca cero.
- La velocidad aparente usa desplazamiento esférico y tiempo real entre muestras. `--jump-mps` es un umbral de demostración, no un límite físico universal.
- Media, mediana/p50, p95 por rango más próximo y RMSE solo usan parejas válidas. Se cuentan parejas ausentes; sin parejas, errores nulos.
- La incertidumbre declarada se mantiene separada del error frente a referencia. No se supone nivel de confianza ni se calibra una garantía de precisión.
- JSON mantiene claves inglesas con unidades. El resumen humano admite ES/EN; los mensajes de validación están en inglés.

## Código y frontera nativa

[`capture.py`](gnss_lab/capture.py): parser acotado y muestras inmutables. [`diagnostics.py`](gnss_lab/diagnostics.py): emparejado explícito y estadísticas. [`distance.py`](gnss_lab/distance.py): modelo Python y ABI tipada. [`distance.c`](native/distance.c): kernel C original. [Tests](tests/test_diagnostics.py): entradas inválidas, distancias analíticas, semántica del reporte, CLI y ABI.

Modelo esférico de radio elegido 6.371.000 m, sin geodesia elipsoidal. Python/C se contrastan en cero, ecuador, polos, antimeridiano y antípodas. Que coincidan no prueba precisión física independiente. La ABI devuelve estado y resultado, rechaza puntero nulo o coordenadas inválidas sin sobrescribir la salida.

Solo se carga la biblioteca propia compilada en `build/` cuando se pide `--backend native`. El CSV no elige bibliotecas ni ejecuta comandos. Es interoperabilidad `ctypes` en el host, no JNI Android ni un driver GNSS.

## Evidencia y límites

macOS local: **25 tests sin omitidos**, compilación C con warnings como errores, reportes Python/nativo y resúmenes ES/EN. CI preparada para Python 3.11/3.14 Linux y 3.14 macOS; el resultado real se registra tras ejecutarla.

No se acredita adquisición Android, NMEA/RAW, trazas reales, validación de campo, certificación o navegación. Una evaluación física necesita procedencia, semántica de relojes, referencia defendible e incertidumbre propia.

## Licencia

Código, documentación y datos sintéticos originales: [MIT](LICENSE), Manuel Naval, 2026. Python, compilador y bibliotecas del sistema conservan sus licencias; no se redistribuyen sus fuentes/binarios.
