"""Run P1 and produce machine-readable evidence. No third-party Python packages."""
import argparse
import json
from pathlib import Path
import resource
import subprocess

def sanitizer_error(text):
    return any(s in text for s in ('runtime error:', 'ERROR: AddressSanitizer', 'ERROR: LeakSanitizer'))

p = argparse.ArgumentParser()
p.add_argument('binary', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--baseline', action='store_true')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
r = subprocess.run([str(a.binary)], capture_output=True, text=True, timeout=180)
(a.output / 'tests.log').write_text(r.stdout + r.stderr)
failures = [s for s in r.stdout.splitlines() if s.startswith('FAIL\t')]
passed = [s for s in r.stdout.splitlines() if s.startswith('PASS\t')]
expected = ['quant/negative\t', 'kernel/K512_N1_M1_p1\t', 'graph/K16_N33_M7_t1_s1\t']
ok = (r.returncode == 1 and all(any(x in f for f in failures) for x in expected)) if a.baseline else (r.returncode == 0 and not failures and len(passed) >= 164)
ok &= not sanitizer_error(r.stdout+r.stderr)
invalid = []
if not a.baseline:
    large = subprocess.run([str(a.binary), '--large-workspace'], capture_output=True, text=True, timeout=60)
    (a.output / 'large-workspace.log').write_text(large.stdout+large.stderr)
    ok &= large.returncode == 0 and 'PASS\tgraph/K16384_N1' in large.stdout and not sanitizer_error(large.stdout+large.stderr)
    for mode, value in [('pack', '4'), ('pack', '20'), ('kernel', '4'), ('kernel', '20'), ('kernel', '16777216')]:
        q = subprocess.run([str(a.binary), '--invalid-'+mode, value], capture_output=True, text=True, timeout=30)
        # SIGABRT from an explicit GGML assertion, not an arbitrary segfault.
        rejected = q.returncode == -6 and 'GGML_ASSERT' in q.stderr and not sanitizer_error(q.stdout+q.stderr)
        (a.output / f'invalid-{mode}-{value}.log').write_text(q.stdout + q.stderr)
        invalid.append(dict(mode=mode, K=int(value), returncode=q.returncode, passed=rejected))
        ok &= rejected
result = dict(mode='author-counterexamples' if a.baseline else 'fixed-regression',
              passed=ok, returncode=r.returncode, passed_checks=len(passed),
              failed_checks=len(failures), failures=failures, invalid_shapes=invalid,
              model_inference=False, performance_measurement=False)
if not a.baseline:
    result['large_workspace_returncode'] = large.returncode
(a.output / 'summary.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if ok else 1)
