"""I1 correctness gate, including explicit assertion (not segfault) rejection tests."""
import argparse
import json
from pathlib import Path
import resource
import subprocess

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('binary',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--counterexamples',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    result=subprocess.run([str(args.binary)],capture_output=True,text=True,timeout=240)
    text=result.stdout+result.stderr
    (args.output/'tests.log').write_text(text)
    passed=[line for line in result.stdout.splitlines() if line.startswith('PASS\t')]
    failed=[line for line in result.stdout.splitlines() if line.startswith('FAIL\t')]
    sanitizer=any(marker in text for marker in ('runtime error:','ERROR: AddressSanitizer','ERROR: LeakSanitizer'))
    ok=result.returncode==0 and len(passed)==225 and not failed and not sanitizer
    invalid=[]
    if args.counterexamples:
        ok=result.returncode==1 and bool(failed) and not sanitizer
        ok &= any('kernel/K640_N33_M3_p1\t' in line for line in failed)
        ok &= any('graph/K36_N33_M7_t4_s1\t' in line for line in failed)
    else:
        small=subprocess.run([str(args.binary),'--small-graph'],capture_output=True,text=True,timeout=30)
        (args.output/'small-graph.log').write_text(small.stdout+small.stderr)
        ok &= small.returncode==0 and 'PASS\tgraph/K4_N33' in small.stdout
        for mode,value in [('pack','0'),('pack','6'),('kernel','0'),('kernel','6'),('kernel','16777216')]:
            rejected=subprocess.run([str(args.binary),'--invalid-'+mode,value],capture_output=True,text=True,timeout=30)
            (args.output/f'invalid-{mode}-{value}.log').write_text(rejected.stdout+rejected.stderr)
            valid=rejected.returncode==-6 and 'GGML_ASSERT' in rejected.stderr
            invalid.append(dict(mode=mode,K=int(value),passed=valid,returncode=rejected.returncode))
            ok &= valid
    summary=dict(passed=bool(ok),mode='counterexamples' if args.counterexamples else 'fixed-regression',
                 passed_checks=len(passed),failed_checks=len(failed),failures=failed,
                 returncode=result.returncode,invalid_shapes=invalid,sanitizer_error=sanitizer)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
