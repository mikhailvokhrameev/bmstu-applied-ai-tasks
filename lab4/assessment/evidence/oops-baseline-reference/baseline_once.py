"""Exactly one full baseline request to the approved official local REST."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import Request,urlopen

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
REFERENCE=PROJECT/'lab4/assessment/evidence/oops-reference'
OUTPUT=PROJECT/'lab4/assessment/evidence/oops-baseline-reference'
CORE=PROJECT/'lab2/ontology/videocard.owl'
ENDPOINT='http://127.0.0.1:11438/oops-reference/rest'
EXPECTED='d8ac600a45ce642deee38be726ae5d0d81f9e47967a9e1bb07a66b5005ae3661'
body=CORE.read_bytes()
if hashlib.sha256(body).hexdigest()!=EXPECTED:raise ValueError('Original baseline checksum mismatch')
if not json.loads((REFERENCE/'fixture-summary.json').read_text())['all_passed']:
    raise ValueError('Reference fixtures are not qualified')
# An existing directory records a previous or uncertain attempt. Never retry.
OUTPUT.mkdir(parents=True,exist_ok=False)
xml=('<?xml version="1.0" encoding="UTF-8"?><OOPSRequest><OntologyUrl></OntologyUrl><OntologyContent><![CDATA['+
     body.decode().replace(']]>',']]]]><![CDATA[>')+
     ']]></OntologyContent><Pitfalls>4,8,10,11,13,22</Pitfalls></OOPSRequest>').encode()
(OUTPUT/'request.xml').write_bytes(xml)
record=dict(service='Self-hosted official upstream OOPS REST; not public production',
            endpoint=ENDPOINT,upstream_commit='11572ea6b31cba29dd3f8a443e24311652f059de',
            war_sha256=json.loads((REFERENCE/'server.json').read_text())['war_sha256'],
            core_sha256=EXPECTED,input_bytes=len(body),request_sha256=hashlib.sha256(xml).hexdigest(),
            pitfalls=['P04','P08','P10','P11','P13','P22'],attempts=1,started_at=time.time(),
            content_type='application/xml',accept='text/turtle')
(OUTPUT/'result.json').write_text(json.dumps(record,indent=2)+'\n')
try:
    with urlopen(Request(ENDPOINT,data=xml,headers={'Content-Type':'application/xml','Accept':'text/turtle'}),timeout=90) as response:
        result=response.read()
        record.update(http_status=response.status,response_content_type=response.headers.get('Content-Type'),
                      response_sha256=hashlib.sha256(result).hexdigest(),response_bytes=len(result))
    (OUTPUT/'response.ttl').write_bytes(result)
except Exception as error:
    record.update(error=type(error).__name__+': '+str(error)[:300],outcome='unknown or failed; not retried')
finally:
    record.update(ended_at=time.time(),seconds=time.time()-record['started_at'])
    (OUTPUT/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    server=json.loads((REFERENCE/'server.json').read_text())
    server.update(baseline_sent=True,baseline_attempts=1,baseline_evidence=str(OUTPUT),
                  baseline_outcome='response saved' if (OUTPUT/'response.ttl').exists() else 'unknown or failed; not retried')
    (REFERENCE/'server.json').write_text(json.dumps(server,indent=2)+'\n')
print(json.dumps(record))
raise SystemExit(0 if (OUTPUT/'response.ttl').exists() else 1)
