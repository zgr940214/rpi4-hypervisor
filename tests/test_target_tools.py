import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "scripts/target"
UUID = "11223344-1122-3344-5566-778899aabbcc"
FAKE_XL = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
p = pathlib.Path(os.environ['FAKE_STATE'])
s = json.loads(p.read_text())
args = sys.argv[1:]
with pathlib.Path(os.environ['FAKE_LOG']).open('a') as log:
    log.write(' '.join(args) + '\n')
command = args[0]
if command == 'list':
    if s.get('list_error'): sys.exit(4)
    s['list_count'] = s.get('list_count', 0) + 1
    if s.get('running_on_recheck') and s['list_count'] == 2:
        s['state'] = 'r-----'
    if s.get('replace_on_recheck') and s['list_count'] == 2:
        s['uuid'] = 'ffeeddcc-bbaa-9988-7766-554433221100'
    print('Name ID Mem VCPUs State Time(s) UUID Reason-Code Security Label')
    print('Domain-0 0 512 4 r----- 2.0 00000000-0000-0000-0000-000000000000')
    if s.get('exists', True):
        print('guest1', s.get('id', 7), '256 1', s.get('state', '-b----'), '1.0', s['uuid'])
elif command == 'create':
    s['exists'] = True
elif command == 'pause':
    s['state'] = '--p---'
elif command == 'unpause':
    if s.get('unpause_error'): sys.exit(5)
    s['state'] = '-b----'
p.write_text(json.dumps(s))
if command == 'pause' and s.get('pause_error'): sys.exit(6)
'''
FAKE_SLEEP = r'''#!/usr/bin/env python3
import json, os, pathlib, time
p = pathlib.Path(os.environ['FAKE_STATE'])
s = json.loads(p.read_text())
if s.get('replace_on_sleep'):
    s['uuid'] = 'ffeeddcc-bbaa-9988-7766-554433221100'
    p.write_text(json.dumps(s))
if s.get('wait_on_sleep'):
    pathlib.Path(os.environ['FAKE_SLEEP_READY']).write_text('ready')
    time.sleep(30)
'''


class TargetTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, contents in [('xl', FAKE_XL), ('sleep', FAKE_SLEEP),
                               ('id', '#!/bin/sh\necho 0\n')]:
            path = self.root / name
            path.write_text(contents)
            path.chmod(0o755)
        self.state = self.root / 'state.json'
        self.log = self.root / 'calls'
        self.env = dict(os.environ, PATH=str(self.root) + ':' + os.environ['PATH'],
                        FAKE_STATE=str(self.state), FAKE_LOG=str(self.log),
                        FAKE_SLEEP_READY=str(self.root / 'sleep-ready'),
                        GUEST1_LOCK_DIR=str(self.root / 'lock'))
        self.configure()

    def configure(self, **kw):
        self.state.write_text(json.dumps(dict(uuid=UUID, **kw)))

    def run_tool(self, name, *args):
        return subprocess.run(['sh', str(TOOLS / name), *args], env=self.env,
                              text=True, capture_output=True, timeout=10)

    def mutations(self):
        if not self.log.exists():
            return []
        return [line for line in self.log.read_text().splitlines()
                if not line.startswith('list ')]

    def test_pause_resumes_same_domain(self):
        result = self.run_tool('guest1-pause-demo', '1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations(), ['pause 7', 'unpause 7'])
        self.assertFalse((self.root / 'lock').exists())

    def test_originally_paused_is_untouched(self):
        self.configure(state='--p---')
        self.assertNotEqual(self.run_tool('guest1-pause-demo').returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_normal_running_blocked_transition_is_allowed(self):
        self.configure(running_on_recheck=True)
        result = self.run_tool('guest1-pause-demo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mutations(), ['pause 7', 'unpause 7'])

    def test_replacement_before_pause_is_rejected(self):
        self.configure(replace_on_recheck=True)
        self.assertNotEqual(self.run_tool('guest1-pause-demo').returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_domain_zero_is_never_mutated(self):
        self.configure(id=0)
        self.assertNotEqual(self.run_tool('guest1-pause-demo').returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_replaced_domain_is_not_resumed(self):
        self.configure(replace_on_sleep=True)
        self.assertNotEqual(self.run_tool('guest1-pause-demo').returncode, 0)
        self.assertEqual(self.mutations(), ['pause 7'])

    def test_pause_failure_after_side_effect_still_cleans_up(self):
        self.configure(pause_error=True)
        self.assertNotEqual(self.run_tool('guest1-pause-demo').returncode, 0)
        self.assertEqual(self.mutations(), ['pause 7', 'unpause 7'])

    def test_unpause_failure_is_failure(self):
        self.configure(unpause_error=True)
        result = self.run_tool('guest1-pause-demo')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unpause failed', result.stderr)

    def test_termination_resumes_guest(self):
        self.configure(wait_on_sleep=True)
        proc = subprocess.Popen(['sh', str(TOOLS / 'guest1-pause-demo')], env=self.env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if (self.root / 'sleep-ready').exists():
                    break
                if proc.poll() is not None:
                    self.fail('demo exited before entering pause interval')
                time.sleep(0.03)
            else:
                self.fail('demo did not enter pause interval')
            proc.terminate()
            proc.communicate(timeout=5)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(self.mutations(), ['pause 7', 'unpause 7'])
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()

    def test_existing_guest_is_not_created(self):
        self.assertEqual(self.run_tool('guest1-start').returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_absent_guest_is_created_once(self):
        self.configure(exists=False)
        self.assertEqual(self.run_tool('guest1-start').returncode, 0)
        self.assertEqual(self.run_tool('guest1-start').returncode, 0)
        self.assertEqual(self.mutations(), ['create /etc/xen/guest1.cfg'])

    def test_query_failure_does_not_create(self):
        self.configure(list_error=True)
        self.assertNotEqual(self.run_tool('guest1-start').returncode, 0)
        self.assertEqual(self.mutations(), [])

    def test_existing_guest_console(self):
        self.assertEqual(self.run_tool('guest1-start', '--console').returncode, 0)
        self.assertEqual(self.mutations(), ['console 7'])

    def test_new_guest_attaches_during_creation(self):
        self.configure(exists=False)
        self.assertEqual(self.run_tool('guest1-start', '--console').returncode, 0)
        self.assertEqual(self.mutations(), ['create -c /etc/xen/guest1.cfg'])

    def test_counter_is_finite(self):
        result = self.run_tool('guest1-counter', '3')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 3)
        self.assertNotEqual(self.run_tool('guest1-counter', '0').returncode, 0)
        self.assertNotEqual(self.run_tool('guest1-counter', '999999').returncode, 0)

    def test_pause_duration_is_bounded(self):
        for value in ['0', '31', '-1', 'x']:
            self.assertNotEqual(self.run_tool('guest1-pause-demo', value).returncode, 0)
        self.assertEqual(self.mutations(), [])


if __name__ == '__main__':
    unittest.main()
