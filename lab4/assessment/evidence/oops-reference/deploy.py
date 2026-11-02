"""Run only the official OOPS WAR in an isolated loopback Tomcat instance."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
EVIDENCE=PROJECT/('docs/assessment/evidence/oops-reference' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment/evidence/oops-reference')
JDK=PROJECT/'.local-runtime/jdk-17.0.21+9/Contents/Home'
TOMCAT_DIST=BASE/'apache-tomcat-10.1.61'
INSTANCE=BASE/'tomcat-instance'
SOURCE=BASE/'OOPS-11572ea6b31cba29dd3f8a443e24311652f059de'
WAR=SOURCE/'target/oops-0.3.0-SNAPSHOT.war'

for port in (11438,11439):
    with socket.socket() as sock:sock.bind(('127.0.0.1',port))
if INSTANCE.exists():raise FileExistsError('Tomcat instance already exists')
shutil.copytree(TOMCAT_DIST/'conf',INSTANCE/'conf')
for name in ('logs','temp','work','webapps'):(INSTANCE/name).mkdir()
config=ET.parse(INSTANCE/'conf/server.xml')
server=config.getroot();server.set('port','11439');server.set('address','127.0.0.1')
connectors=config.findall('.//Connector')
if len(connectors)!=1:raise ValueError('Unexpected live Tomcat connectors')
for key,value in dict(port='11438',address='127.0.0.1',maxThreads='4',minSpareThreads='1',acceptCount='10').items():
    connectors[0].set(key,value)
config.write(INSTANCE/'conf/server.xml',encoding='utf-8',xml_declaration=True)
shutil.copyfile(WAR,INSTANCE/'webapps/oops-reference.war')
env=dict(JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin',
         CATALINA_HOME=str(TOMCAT_DIST),CATALINA_BASE=str(INSTANCE),
         CATALINA_OPTS='-Xms128m -Xmx768m -XX:ActiveProcessorCount=2 -Djava.awt.headless=true',
         LANG='en_US.UTF-8')
command=['/usr/bin/nice','-n','10',str(TOMCAT_DIST/'bin/catalina.sh'),'run']
with (BASE/'tomcat-console.log').open('xb') as log:
    process=subprocess.Popen(command,env=env,cwd=INSTANCE,stdout=log,stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL,start_new_session=True)
metadata=dict(pid=process.pid,started_at=time.time(),command=command,
              upstream_commit='11572ea6b31cba29dd3f8a443e24311652f059de',
              endpoint='http://127.0.0.1:11438/oops-reference/rest',http_port=11438,
              shutdown_port=11439,bind='127.0.0.1',manager_deployed=False,
              java_home=str(JDK),tomcat_version='10.1.61',active_processors=2,
              war_sha256=hashlib.sha256(WAR.read_bytes()).hexdigest(),
              instance=str(INSTANCE),console_log=str(BASE/'tomcat-console.log'),
              status='starting; no ontology has been sent')
(EVIDENCE/'server.json').write_text(json.dumps(metadata,indent=2)+'\n')
(BASE/'tomcat.pid').write_text(str(process.pid)+'\n')
print(json.dumps(metadata))
