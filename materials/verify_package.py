from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
m=json.loads((p/'MANIFEST.json').read_text('utf-8'))
for name,expected in m['files'].items():
 f=p/name
 assert hashlib.sha256(f.read_bytes()).hexdigest()==expected, name
rows=[json.loads(s) for s in (p/'results/jobs.jsonl').read_text('utf-8').split('\n') if s.strip()]
ids=[(r['company_name'],r['source_job_id'] or r['detail_url'].split('?')[0]) for r in rows]
assert len(rows)==len(set(ids))==5213
print(f'OK: {len(m["files"])} files verified; {len(rows)} unique jobs.')
