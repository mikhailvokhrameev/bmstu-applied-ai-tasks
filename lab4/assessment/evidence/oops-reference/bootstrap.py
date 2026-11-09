"""Fetch pinned official source/tool archives and verify Apache SHA-512 files."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import tarfile
import time
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
EVIDENCE = PROJECT/('docs/assessment/evidence/oops-reference' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment/evidence/oops-reference')
COMMIT = '11572ea6b31cba29dd3f8a443e24311652f059de'
PACKAGES = [
    dict(name='apache-maven-3.9.16-bin.tar.gz',
         url='https://dlcdn.apache.org/maven/maven-3/3.9.16/binaries/apache-maven-3.9.16-bin.tar.gz',
         checksum='https://downloads.apache.org/maven/maven-3/3.9.16/binaries/apache-maven-3.9.16-bin.tar.gz.sha512',
         directory='apache-maven-3.9.16'),
    dict(name='apache-tomcat-10.1.61.tar.gz',
         url='https://dlcdn.apache.org/tomcat/tomcat-10/v10.1.61/bin/apache-tomcat-10.1.61.tar.gz',
         checksum='https://downloads.apache.org/tomcat/tomcat-10/v10.1.61/bin/apache-tomcat-10.1.61.tar.gz.sha512',
         directory='apache-tomcat-10.1.61'),
    dict(name='OOPS-'+COMMIT+'.tar.gz',url='https://codeload.github.com/oeg-upm/OOPS/tar.gz/'+COMMIT,
         directory='OOPS-'+COMMIT),
]

def get(url):
    with urlopen(Request(url,headers={'User-Agent':'Ontology-official-reference-setup'}),timeout=90) as response:
        return response.read()

def install(spec):
    started=time.monotonic()
    path=BASE/spec['name']
    content=path.read_bytes() if path.exists() else get(spec['url'])
    actual=hashlib.sha512(content).hexdigest()
    expected=None
    if spec.get('checksum'):
        checksum=get(spec['checksum'])
        expected=re.search(rb'\b[0-9a-fA-F]{128}\b',checksum).group().decode().lower()
        if actual!=expected:raise ValueError('Apache SHA-512 mismatch: '+spec['name'])
        (BASE/(spec['name']+'.sha512')).write_bytes(checksum)
    if not path.exists():
        with path.open('xb') as output:output.write(content)
    destination=BASE/spec['directory']
    if not destination.exists():
        with tarfile.open(path,'r:gz') as archive:
            for member in archive.getmembers():
                target=(BASE/member.name).resolve()
                if (not target.is_relative_to(destination.resolve()) or member.issym()
                        or member.islnk() or not (member.isdir() or member.isfile())):
                    raise ValueError('Unsafe archive entry: '+member.name)
            archive.extractall(BASE)
    return dict(**spec,bytes=len(content),sha512=actual,apache_sha512_verified=expected is not None,
                seconds=round(time.monotonic()-started,3))

EVIDENCE.mkdir(parents=True,exist_ok=True)
results=list(ThreadPoolExecutor(max_workers=3).map(install,PACKAGES))
metadata=dict(upstream='https://github.com/oeg-upm/OOPS',commit=COMMIT,
              interpretation='Self-hosted official upstream REST reference; not the public production endpoint',packages=results)
with (EVIDENCE/'bootstrap.json').open('x',encoding='utf-8') as output:
    json.dump(metadata,output,ensure_ascii=False,indent=2);output.write('\n')
print(json.dumps(dict(downloaded=[r['directory'] for r in results],apache_verified=True,commit=COMMIT)))
