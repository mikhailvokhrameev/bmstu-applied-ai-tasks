"""Send only pinned upstream test ontologies to the isolated official REST."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.request import Request,urlopen

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
EVIDENCE=PROJECT/('docs/assessment/evidence/oops-reference' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment/evidence/oops-reference')
DATA=BASE/'OOPS-11572ea6b31cba29dd3f8a443e24311652f059de/src/test/resources/data'
JDK=PROJECT/'.local-runtime/jdk-17.0.21+9/Contents/Home'
LIB=BASE/'tomcat-instance/webapps/oops-reference/WEB-INF/lib/*'
ENDPOINT='http://127.0.0.1:11438/oops-reference/rest'
CASES=['P04','P08','P10','P10-A','P10-B','P10-C','P11','P13','P22M1','P22M2','P22M3','P22M4']
ENV=dict(PATH=str(JDK/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin',LANG='en_US.UTF-8')
CLASSES=BASE/'fixture-comparator';CLASSES.mkdir(exist_ok=True)
compiled=subprocess.run([str(JDK/'bin/javac'),'-encoding','UTF-8','-cp',str(LIB),'-d',str(CLASSES),str(BASE/'CompareFixtures.java')],env=ENV,capture_output=True,text=True)
if compiled.returncode:raise RuntimeError(compiled.stderr[-3000:])
shutil.copyfile(BASE/'CompareFixtures.java',EVIDENCE/'CompareFixtures.java')
results=[]
for case in CASES:
    folder=EVIDENCE/'fixtures'/case;folder.mkdir(parents=True,exist_ok=False)
    ontology=(DATA/'input'/f'{case}.owl').read_bytes()
    expected=DATA/'output'/f'{case}.ttl'
    (folder/'input.owl').write_bytes(ontology)
    shutil.copyfile(expected,folder/'upstream-expected.ttl')
    family=re.match(r'P\d+',case).group()
    xml=('<?xml version="1.0" encoding="UTF-8"?><OOPSRequest><OntologyUrl></OntologyUrl><OntologyContent><![CDATA['+
         ontology.decode().replace(']]>',']]]]><![CDATA[>')+
         ']]></OntologyContent><Pitfalls>'+str(int(family[1:]))+'</Pitfalls></OOPSRequest>').encode()
    (folder/'request.xml').write_bytes(xml)
    started=time.monotonic()
    record=dict(case=case,family=family,endpoint=ENDPOINT,input_sha256=hashlib.sha256(ontology).hexdigest(),
                upstream_expected_sha256=hashlib.sha256(expected.read_bytes()).hexdigest())
    try:
        with urlopen(Request(ENDPOINT,data=xml,headers={'Content-Type':'application/xml','Accept':'text/turtle'}),timeout=60) as response:
            body=response.read();record.update(http_status=response.status,content_type=response.headers.get('Content-Type'))
        (folder/'actual.ttl').write_bytes(body)
        record['response_sha256']=hashlib.sha256(body).hexdigest()
        command=[str(JDK/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-cp',str(CLASSES)+':'+str(LIB),
                 'CompareFixtures',str(folder/'upstream-expected.ttl'),str(folder/'actual.ttl'),family]
        compared=subprocess.run(command,env=ENV,text=True,capture_output=True,timeout=60)
        (folder/'comparison.stderr.txt').write_text(compared.stderr)
        if compared.returncode:raise RuntimeError('Comparator failed: '+compared.stderr[-1200:])
        record.update(json.loads(compared.stdout))
    except Exception as error:
        record.update(matches=False,error=type(error).__name__+': '+str(error)[:300])
    record['seconds']=round(time.monotonic()-started,3)
    (folder/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    results.append(record)
    print(json.dumps(record,ensure_ascii=False),flush=True)
summary=dict(upstream_commit='11572ea6b31cba29dd3f8a443e24311652f059de',endpoint=ENDPOINT,
             scope='Official upstream synthetic fixtures only; no lab ontology was sent',
             all_passed=all(row['matches'] for row in results),passed=sum(row['matches'] for row in results),
             total=len(results),results=results)
(EVIDENCE/'fixture-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(all_passed=summary['all_passed'],passed=summary['passed'],total=summary['total'])))
raise SystemExit(0 if summary['all_passed'] else 1)
