"""Prepared capability only: one explicit final-file request, never auto-run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
ASSESSMENT=PROJECT/('docs/assessment' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment')
REFERENCE=ASSESSMENT/'evidence/oops-reference'
ENDPOINT='http://127.0.0.1:11438/oops-reference/rest'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ontology',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.sha256):raise ValueError('Explicit final SHA-256 required')
    content=args.ontology.read_bytes()
    if hashlib.sha256(content).hexdigest()!=args.sha256:raise ValueError('Final checksum mismatch')
    ns=dict(owl='http://www.w3.org/2002/07/owl#',rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#')
    header=ET.fromstring(content).find('owl:Ontology',ns)
    if (header is None or header.find('owl:versionIRI',ns) is None or
            header.find('owl:versionIRI',ns).get('{'+ns['rdf']+'}resource')!='https://example.org/ontologies/videocard/2.0.0'):
        raise ValueError('Expected the accepted version-2.0.0 file, not the original baseline')
    server=json.loads((REFERENCE/'server.json').read_text())
    if server.get('final_sent'):raise ValueError('A final request was already attempted; do not retry')
    if not server.get('official_fixtures_passed'):raise ValueError('Reference fixtures are not qualified')
    jdk=PROJECT/'.local-runtime/jdk-17.0.21+9/Contents/Home'
    lib=BASE/'tomcat-instance/webapps/oops-reference/WEB-INF/lib/*'
    classes=BASE/'fixture-comparator'
    env=dict(PATH=str(jdk/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin',LANG='en_US.UTF-8')
    compiled=subprocess.run([str(jdk/'bin/javac'),'-encoding','UTF-8','-cp',str(lib),'-d',str(classes),str(BASE/'SummarizeReport.java')],
                            env=env,capture_output=True,text=True)
    if compiled.returncode:raise RuntimeError('Report parser compilation failed')
    args.output.mkdir(parents=True,exist_ok=False)
    xml=('<?xml version="1.0" encoding="UTF-8"?><OOPSRequest><OntologyUrl></OntologyUrl><OntologyContent><![CDATA['+
         content.decode().replace(']]>',']]]]><![CDATA[>')+
         ']]></OntologyContent><Pitfalls>4,8,10,11,13,22</Pitfalls></OOPSRequest>').encode()
    (args.output/'request.xml').write_bytes(xml)
    record=dict(service='Self-hosted official upstream OOPS REST; not public production',endpoint=ENDPOINT,
                upstream_commit=server['upstream_commit'],war_sha256=server['war_sha256'],
                final_sha256=args.sha256,input_bytes=len(content),pitfalls=['P04','P08','P10','P11','P13','P22'],
                request_sha256=hashlib.sha256(xml).hexdigest(),attempts=1,started_at=time.time())
    server.update(final_sent=True,final_attempts=1,final_sha256=args.sha256,final_evidence=str(args.output),
                  final_outcome='attempt recorded; response pending')
    (REFERENCE/'server.json').write_text(json.dumps(server,indent=2)+'\n')
    try:
        with urlopen(Request(ENDPOINT,data=xml,headers={'Content-Type':'application/xml','Accept':'text/turtle'}),timeout=90) as response:
            result=response.read()
            record.update(http_status=response.status,content_type=response.headers.get('Content-Type'),
                          response_sha256=hashlib.sha256(result).hexdigest())
        (args.output/'response.ttl').write_bytes(result)
        parsed=subprocess.run([str(jdk/'bin/java'),'-Xmx256m','-XX:ActiveProcessorCount=2','-cp',str(classes)+':'+str(lib),
                               'SummarizeReport',str(args.output/'response.ttl')],env=env,capture_output=True,text=True,timeout=60)
        if parsed.returncode:raise RuntimeError('Official response RDF parsing failed')
        summary=json.loads(parsed.stdout)
        if not summary['response_present']:raise ValueError('No genuine RDF response in body')
        (args.output/'upstream-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        record['rdf_response_verified']=True
    except Exception as error:
        record.update(error=type(error).__name__+': '+str(error)[:300],outcome='unknown or failed; not retried')
    finally:
        record.update(ended_at=time.time(),seconds=time.time()-record['started_at'])
        (args.output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        server['final_outcome']='verified RDF response saved' if record.get('rdf_response_verified') else 'unknown or failed; not retried'
        (REFERENCE/'server.json').write_text(json.dumps(server,indent=2)+'\n')
    print(json.dumps(record))
    return 0 if record.get('rdf_response_verified') else 1

if __name__=='__main__':raise SystemExit(main())
