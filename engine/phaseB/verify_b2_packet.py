#!/usr/bin/env python3
"""Read-only release-packet consistency check (not an engine or scientific validator).

Usage: python verify_b2_packet.py package.zip --output check.json
       python verify_b2_packet.py /path/to/phaseB --output check.json

Checks current module/test/fixture/asset/doc SHA values and current addendum counts.
Historical audit supplements are intentionally NOT treated as current expected hashes.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,re,sys,zipfile
from pathlib import Path,PurePosixPath

def read_packet(path:Path)->dict[str,bytes]:
    if path.is_dir():
        if (path/'phaseB').is_dir():path=path/'phaseB'
        return {p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    with zipfile.ZipFile(path) as z:
        names=[i.filename for i in z.infolist() if not i.is_dir()]
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP member names')
        for name in names:
            q=PurePosixPath(name)
            if q.is_absolute() or '..' in q.parts:raise ValueError('Unsafe ZIP member name')
        candidates=[n for n in names if n.endswith('B2_completion_inventory.json')]
        if len(candidates)!=1:raise ValueError('Expected one current inventory')
        prefix=candidates[0][:-len('B2_completion_inventory.json')]
        return {n[len(prefix):]:z.read(n) for n in names if n.startswith(prefix)}

def check(data:dict[str,bytes])->dict:
    inv=json.loads(data['B2_completion_inventory.json']);failures=[];sha_results=[]
    for category,prefix in [('modules','step1_engine/'),('tests_sha256','tests/'),('fixtures_sha256','tests/'),('assets_sha256',''),('documents_sha256',''),('b3_sha256',''),('registered_assets_sha256',''),('d_sha256','')]:
        for name,expected in inv[category].items():
            key=prefix+name;actual=hashlib.sha256(data[key]).hexdigest() if key in data else None
            sha_results.append({'category':category,'path':key,'expected':expected,'actual':actual,'ok':actual==expected})
            if actual!=expected:failures.append('SHA mismatch or missing file: '+key)
    modules=[p for p in data if p.startswith('step1_engine/') and p.count('/')==1 and p.endswith('.py')]
    tests=[p for p in data if p.startswith('tests/test') and p.count('/')==1 and p.endswith('.py')]
    function_counts={Path(p).name:sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(data[p].decode('utf-8')))) for p in tests}
    counts={'modules':len(modules),'test_files':len(tests),'test_functions':sum(function_counts.values()),'test_b_files':sum(Path(p).name.startswith('test_b') for p in tests),'test_audit_files':sum(Path(p).name.startswith('test_audit') for p in tests)}
    if counts!=inv['counts'] or function_counts!=inv['tests']:failures.append('Inventory counts differ from files')
    if set(inv['modules'])!={Path(p).name for p in modules}:failures.append('Module inventory is not exact')
    if set(inv['tests_sha256'])!=set(function_counts):failures.append('Test SHA inventory is not exact')
    version=re.search(r'__version__\s*=\s*[\'"]([^\'"]+)',data['step1_engine/__init__.py'].decode()).group(1)
    if inv['engine_version']!=version:failures.append('Inventory engine version differs from source')
    spec=data['Step1_PhaseB_engine_spec_v0.3_addendum.md'].decode()
    sv=re.search(r'step1_engine ([\d.]+)',spec).group(1)
    if sv!=version:failures.append(f'Current addendum version {sv} differs from source {version}')
    line=next((s for s in spec.splitlines() if s.startswith('受入テスト')),'')
    patterns={'modules':r'(\d+) module','test_files':r'(\d+) test file','test_functions':r'(\d+) test 関数','test_b_files':r'`test_b\*` (\d+)','test_audit_files':r'`test_audit\*` (\d+)'}
    for key,pat in patterns.items():
        m=re.search(pat,line)
        if not m or int(m.group(1))!=counts[key]:failures.append('Current addendum count mismatch: '+key)
    # Only compares claimed counts in the supplied log. Independent pytest is a separate audit step.
    lines=data.get('test_log.txt',b'').decode(errors='replace').splitlines()
    nodes=re.findall(r'^(tests/\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)\b','\n'.join(lines),re.M)
    ncases=len(nodes);m=re.search(r'(\d+) pytest case',line)
    if not m or int(m.group(1))!=ncases:failures.append(f'Current addendum pytest-case count differs from {ncases} supplied log entries')
    return {'scope':'Packet metadata consistency only. Does not execute tests, authenticate logs, validate external assets, or authorize freeze.','passed':not failures,'engine_version':version,'counts':counts,'supplied_log_entries':ncases,'sha_entries':len(sha_results),'sha_checks':sha_results,'failures':failures}

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('packet',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:result=check(read_packet(args.packet))
    except (ValueError,KeyError,OSError,zipfile.BadZipFile,SyntaxError) as e:
        result={'passed':False,'scope':'Packet metadata consistency only','error':str(e)}
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(text+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='sha_checks'},ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':sys.exit(main())
