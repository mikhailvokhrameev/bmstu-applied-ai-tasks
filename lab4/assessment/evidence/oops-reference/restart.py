"""Restart the already qualified official OOPS instance without resetting its request ledger."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
EVIDENCE = PROJECT / ('docs/assessment/evidence/oops-reference' if (PROJECT/'DELIVERY_MANIFEST.json').is_file() else 'lab4/assessment/evidence/oops-reference')
server_path = EVIDENCE / 'server.json'
server = json.loads(server_path.read_text())
if server.get('official_fixtures_passed') is not True:
    raise ValueError('The existing instance is not qualified')
source = BASE / ('OOPS-' + server['upstream_commit'])
expected = json.loads((EVIDENCE/'upstream-source-sha256.json').read_text())
for name, value in expected.items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest() != value:
        raise ValueError('Upstream source changed: ' + name)
instance = BASE/'tomcat-instance'
war = instance/'webapps/oops-reference.war'
if hashlib.sha256(war.read_bytes()).hexdigest() != server['war_sha256']:
    raise ValueError('Deployed WAR changed')
for port in (11438, 11439):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))
jdk = PROJECT/'.local-runtime/jdk-17.0.21+9/Contents/Home'
distribution = BASE/'apache-tomcat-10.1.61'
env = dict(JAVA_HOME=str(jdk), PATH=str(jdk/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin',
           CATALINA_HOME=str(distribution), CATALINA_BASE=str(instance),
           CATALINA_OPTS='-Xms128m -Xmx768m -XX:ActiveProcessorCount=2 -Djava.awt.headless=true',
           LANG='en_US.UTF-8')
started = time.time()
log_path = BASE/('tomcat-restart-' + str(int(started)) + '.log')
command = ['/usr/bin/nice', '-n', '10', str(distribution/'bin/catalina.sh'), 'run']
with log_path.open('xb') as log:
    process = subprocess.Popen(command, env=env, cwd=instance, stdout=log,
                               stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
record = dict(pid=process.pid, started_at=started, command=command, console_log=str(log_path),
              baseline_sent_preserved=server['baseline_sent'], final_sent_preserved=server['final_sent'],
              upstream_source_hashes_verified=len(expected), war_sha256=server['war_sha256'])
server.setdefault('restarts', []).append(record)
server['pid'] = process.pid
server['status'] = 'restarting qualified instance; no ontology submitted by restart'
server_path.write_text(json.dumps(server, indent=2)+'\n')
(BASE/'tomcat.pid').write_text(str(process.pid)+'\n')
(EVIDENCE/('restart-'+str(int(started))+'.json')).write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record))
