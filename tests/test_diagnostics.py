import contextlib
import ctypes
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from gnss_lab.capture import HEADER, MAX_BYTES, MAX_ROWS, Sample, read_capture
from gnss_lab.diagnostics import analyze
from gnss_lab.distance import NativeDistance, RADIUS_M, distance_m
from gnss_lab.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


class CaptureTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'capture.csv'

    def read(self, rows, header=None):
        self.path.write_text(','.join(HEADER if header is None else header) + '\n' + rows)
        return read_capture(self.path)

    def test_synthetic_fixtures_have_explicit_fix_and_missing_states(self):
        observed = read_capture(ROOT / 'examples/observed.csv')
        self.assertEqual(7,len(observed)); self.assertEqual(3,sum(s.has_fix for s in observed))
        self.assertEqual(7,len(read_capture(ROOT / 'examples/reference.csv')))

    def test_header_is_exact_and_ordered(self):
        for header in [list(reversed(HEADER)),HEADER+['extra'],['elapsed_ms','fix']]:
            with self.subTest(header=header), self.assertRaisesRegex(ValueError,'header'):
                self.read('',header)

    def test_missing_fix_never_retains_position_fields(self):
        for row in ['0,0,1,,\n','0,0,,1,\n','0,0,,,2\n']:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError,'empty position'):
                self.read(row)
        self.assertFalse(self.read('0,0,,,\n')[0].has_fix)

    def test_fix_requires_all_finite_fields_in_range(self):
        for row in ['0,1,,,\n','0,1,nan,0,3\n','0,1,0,inf,3\n','0,1,0,0,nan\n','0,1,91,0,3\n','0,1,0,181,3\n','0,1,0,0,-1\n','0,1,0,0,1e308\n','0,2,,,\n']:
            with self.subTest(row=row), self.assertRaises(ValueError): self.read(row)

    def test_duplicate_regressive_and_invalid_timestamps_fail_without_sorting(self):
        for rows in ['0,0,,,\n0,0,,,\n','2,0,,,\n1,0,,,\n','-1,0,,,\n','1.5,0,,,\n','١,0,,,\n','1e3,0,,,\n','9999999999999999,0,,,\n']:
            with self.subTest(rows=rows), self.assertRaises(ValueError): self.read(rows)

    def test_empty_capture_fails(self):
        with self.assertRaisesRegex(ValueError,'empty'): self.read('')

    def test_missing_extra_columns_and_malformed_quotes_fail(self):
        for row in ['0,0,,\n','0,0,,,,extra\n','0,1,"unterminated,0,3\n']:
            with self.subTest(row=row), self.assertRaises(ValueError): self.read(row)
        self.path.write_text('"unterminated header\n')
        with self.assertRaisesRegex(ValueError,'malformed CSV header'): read_capture(self.path)

    def test_byte_and_row_limits_fail(self):
        self.path.write_bytes(b'x'*(MAX_BYTES+1))
        with self.assertRaisesRegex(ValueError,'MiB'): read_capture(self.path)
        with self.assertRaisesRegex(ValueError,'10000'):
            self.read(''.join(f'{n},0,,,\n' for n in range(MAX_ROWS+1)))

    def test_utf8_bom_supported_and_invalid_encoding_fails(self):
        self.path.write_bytes(b'\xef\xbb\xbf'+(','.join(HEADER)+'\n0,0,,,\n').encode())
        self.assertEqual([Sample(0)],read_capture(self.path))
        self.path.write_bytes(b'\xff\xfe')
        with self.assertRaisesRegex(ValueError,'UTF-8'): read_capture(self.path)

    def test_direct_samples_validate_partial_or_invalid_values(self):
        for args in [(0,None,0,None),(-1,),(True,),(0,0,None,3),(0,0,0,None),(0,False,0,3),(0,0,0,1e308),(0,10**1000,0,3)]:
            with self.subTest(args=args), self.assertRaises(ValueError): Sample(*args)


class DiagnosticsTest(unittest.TestCase):
    def test_fixture_exposes_delayed_fix_loss_and_jump(self):
        result = analyze(read_capture(ROOT/'examples/observed.csv'),read_capture(ROOT/'examples/reference.csv'))
        self.assertEqual((3,4,2000),(result['fix_count'],result['no_fix_count'],result['time_to_first_fix_ms']))
        self.assertEqual(3000,result['largest_fix_interval_ms']); self.assertEqual(1,result['gap_count'])
        self.assertEqual(1,result['apparent_speed_jump_count']); self.assertEqual(3,result['matched_fix_count'])
        self.assertGreater(result['error_m']['p95'],100); self.assertEqual(3,result['mean_reported_accuracy_m'])

    def test_known_equatorial_errors_define_mean_median_p95_and_rmse(self):
        measured = [Sample(n*1000,0,n,3) for n in range(3)]
        reference = [Sample(n*1000,0,0,0) for n in range(3)]
        errors = analyze(measured,reference)['error_m']; degree = RADIUS_M*math.pi/180
        self.assertAlmostEqual(degree,errors['mean']); self.assertAlmostEqual(degree,errors['p50'])
        self.assertAlmostEqual(2*degree,errors['p95']); self.assertAlmostEqual(degree*math.sqrt(5/3),errors['rmse'])

    def test_no_fix_produces_null_metrics_not_zero_error_or_fake_ttff(self):
        result=analyze([Sample(0),Sample(2000)],[Sample(0,0,0,0)])
        self.assertIsNone(result['time_to_first_fix_ms']); self.assertIsNone(result['largest_fix_interval_ms'])
        self.assertTrue(all(v is None for v in result['error_m'].values()))
        self.assertEqual(2000,result['tail_without_fix_ms'])

    def test_reference_matching_is_exact_and_missing_pairs_are_counted(self):
        measured=[Sample(0,0,0,3),Sample(1000,0,1,3),Sample(2000,0,2,3)]
        result=analyze(measured,[Sample(0,0,0,0),Sample(999,0,1,0),Sample(2000)])
        self.assertEqual(1,result['matched_fix_count']); self.assertEqual(2,result['unmatched_fix_count'])
        self.assertEqual(0,result['error_m']['rmse'])

    def test_gap_threshold_is_strict_and_tail_is_separate(self):
        measured=[Sample(0,0,0,3),Sample(2500,0,0,3),Sample(5001,0,0,3),Sample(7000)]
        result=analyze(measured,[Sample(0,0,0,0)])
        self.assertEqual(1,result['gap_count']); self.assertEqual(1999,result['tail_without_fix_ms'])

    def test_apparent_speed_uses_actual_elapsed_time_and_strict_threshold(self):
        measured=[Sample(0,0,0,3),Sample(2000,0,1,3)]; threshold=distance_m(0,0,0,1)/2
        self.assertEqual(0,analyze(measured,measured,jump_mps=threshold)['apparent_speed_jump_count'])
        self.assertEqual(1,analyze(measured,measured,jump_mps=threshold-.1)['apparent_speed_jump_count'])

    def test_direct_api_rejects_empty_unordered_and_invalid_thresholds(self):
        valid=[Sample(0)]
        for samples,reference,options in [([],valid,{}),(valid,[],{}),([Sample(1),Sample(0)],valid,{}),(valid,valid,{'max_gap_ms':0}),(valid,valid,{'max_gap_ms':True}),(valid,valid,{'jump_mps':float('nan')}),(valid,valid,{'jump_mps':0}),(valid,valid,{'jump_mps':10**1000})]:
            with self.subTest(options=options),self.assertRaises(ValueError): analyze(samples,reference,**options)


class NativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build is intentionally required: do not turn missing native evidence into a skipped pass.
        cls.native=NativeDistance()

    def test_python_and_c_agree_across_zero_equator_poles_and_antimeridian(self):
        for coordinates in [(0,0,0,0),(0,0,0,1),(0,179.9,0,-179.9),(90,0,90,180),(-90,-180,90,180),(40,-3,-30,150),(0,0,0,180)]:
            with self.subTest(coordinates=coordinates):
                self.assertAlmostEqual(distance_m(*coordinates),self.native(*coordinates),delta=1e-6)

    def test_python_and_native_wrappers_reject_invalid_inputs(self):
        for backend in [distance_m,self.native]:
            for coordinates in [(91,0,0,0),(0,181,0,0),(0,0,float('nan'),0),(0,0,0,float('inf')),(True,0,0,0),(10**1000,0,0,0)]:
                with self.subTest(coordinates=coordinates),self.assertRaises(ValueError): backend(*coordinates)

    def test_raw_c_abi_rejects_invalid_input_without_overwriting_output(self):
        out=ctypes.c_double(123)
        self.assertEqual(1,self.native.function(100,0,0,0,ctypes.byref(out)))
        self.assertEqual(123,out.value)
        self.assertEqual(1,self.native.function(0,0,0,0,None))

    def test_both_backends_produce_same_diagnostic_metrics(self):
        observed=read_capture(ROOT/'examples/observed.csv'); reference=read_capture(ROOT/'examples/reference.csv')
        python=analyze(observed,reference); native=analyze(observed,reference,distance=self.native)
        for metric,value in python.pop('error_m').items():
            self.assertAlmostEqual(value,native['error_m'][metric],delta=1e-6)
        native.pop('error_m')
        self.assertEqual(python,native)


class CliTest(unittest.TestCase):
    def invoke(self,*args):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=main(['--samples',str(ROOT/'examples/observed.csv'),'--reference',str(ROOT/'examples/reference.csv'),*args])
        return code,out.getvalue(),err.getvalue()

    def test_json_is_machine_readable_and_success_is_not_quality_acceptance(self):
        code,out,err=self.invoke()
        self.assertEqual(0,code); self.assertEqual('',err)
        result=json.loads(out); self.assertEqual(1,result['apparent_speed_jump_count'])
        self.assertGreater(result['error_m']['p95'],100)

    def test_text_reports_support_english_and_spanish(self):
        for language,title in [('en','GNSS capture report'),('es','Informe de captura GNSS')]:
            code,out,err=self.invoke('--format','text','--language',language)
            self.assertEqual(0,code); self.assertIn(title,out); self.assertIn('2000 ms',out)

    def test_invalid_input_emits_no_json_and_does_not_echo_paths(self):
        code,out,err=self.invoke('--samples','/nonexistent/private-capture.csv')
        self.assertEqual(2,code); self.assertEqual('',out); self.assertNotIn('private-capture',err)
        code,out,err=self.invoke('--max-gap-ms','0')
        self.assertEqual(2,code); self.assertEqual('',out)
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / 'bad.csv'
            bad.write_text(','.join(HEADER) + '\n0,2,,,\n')
            for language in ['en', 'es']:
                code, out, err = self.invoke('--samples', str(bad), '--language', language)
                self.assertEqual(2, code); self.assertEqual('', out)
                self.assertIn('Row 1' if language == 'en' else 'Fila 1', err)
                self.assertIn('fix', err)
                self.assertNotIn(str(bad), err)

    def test_missing_native_library_gives_recovery_without_leaking_loader_details(self):
        from unittest.mock import patch
        for language in ['en', 'es']:
            with patch('gnss_lab.__main__.NativeDistance', side_effect=OSError('/private/loader-detail')):
                code, out, err = self.invoke('--backend', 'native', '--language', language)
            self.assertEqual(2, code)
            self.assertEqual('', out)
            self.assertIn('tools/build_native.py', err)
            self.assertIn('--backend python', err)
            self.assertNotIn('/private', err)

    def test_native_cli_uses_explicit_backend(self):
        code,out,err=self.invoke('--backend','native')
        self.assertEqual(0,code); self.assertEqual('native',json.loads(out)['backend'])

    def test_text_exposes_reference_error_separately_from_declared_uncertainty(self):
        for language in ['en', 'es']:
            code,out,_=self.invoke('--format','text','--language',language)
            self.assertEqual(0,code)
            self.assertIn('p95: 104.52 m',out)
            self.assertIn('3.00 m',out)
            self.assertIn('> 2500 ms',out); self.assertIn('> 10 m/s',out)
            self.assertIn('do not validate a receiver' if language == 'en' else 'no validan un receptor', out)

    def test_text_never_turns_missing_fix_or_reference_pairs_into_zero_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'no-fix.csv'
            path.write_text(','.join(HEADER)+'\n0,0,,,\n1000,0,,,\n')
            for language,missing in [('en','No data'),('es','Sin datos')]:
                code,out,_=self.invoke('--samples',str(path),'--format','text','--language',language)
                self.assertEqual(0,code)
                self.assertIn('p95: '+missing,out)
                self.assertNotIn('p95: 0',out)
                self.assertIn('No fix' if language=='en' else 'Sin posición',out)


if __name__=='__main__': unittest.main()
