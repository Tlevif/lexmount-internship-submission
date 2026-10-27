from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
m=json.loads((p/'MANIFEST.json').read_text('utf-8'))
for n,d in m['files'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==d,n
rows=[json.loads(x) for x in (p/'results/jobs.jsonl').read_text('utf-8').split('\n') if x]
s=json.loads((p/'SUMMARY.json').read_text('utf-8'))
assert len(rows)==s['jobs']==len({(j['company_name'],j['source_job_id'] or j['detail_url']) for j in rows})
assert all(j['responsibilities'] and j['requirements'] and j['classification']['keep'] for j in rows)
assert not any(j['category'] in ['待审核','待核验','非计算机岗位'] for j in rows)
print(f'OK: {len(m["files"])} files, {len(rows)} complete technical jobs.')
