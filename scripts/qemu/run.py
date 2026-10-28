#!/usr/bin/env python3
"""Boot real Xen/Dom0 in QEMU and exercise guest1 with serial/SSH evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import time
import uuid

import pexpect

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Runner:
    def __init__(self, args):
        self.args = args
        self.output = Path(args.output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.serial = None
        self.console = None
        self.logs = []
        self.prompts = {}
        planned = ['xen_banner', 'xen_and_dom0_boot', 'dom0_toolstack',
                   'guest1_first_boot_and_writable_root', 'dom0_ssh_and_guest_console_reattach',
                   'guest1_pause_resume_and_project_demo', 'guest1_clean_shutdown',
                   'guest1_recreate_and_persistent_root', 'guest1_final_shutdown',
                   'source_disk_unchanged']
        self.report = {
            'started_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'QEMU ARM virt; Xen plus validation rootfs and project guest-management scripts',
            'pi4_image_build': 'NOT_RUN', 'pi4_hardware': 'NOT_RUN',
            'checks': [{'name': name, 'status': 'NOT_RUN', 'detail': 'Not reached yet'} for name in planned],
            'commands': [], 'artifacts': {}, 'status': 'FAIL',
            'disk_mode': 'QEMU -snapshot temporary overlay; base disk hash checked after QEMU exits',
        }

    def record(self, name, status, detail):
        item = next((check for check in self.report['checks'] if check['name'] == name), None)
        if item is None:
            item = {'name': name}
            self.report['checks'].append(item)
        item.update(status=status, detail=detail)
        print(f'{status}: {name}: {detail}', flush=True)
        self.save()

    def save(self):
        (self.output / 'report.json').write_text(json.dumps(self.report, indent=2) + '\n')

    def check(self, name, operation):
        print(f'RUNNING: {name}', flush=True)
        try:
            detail = operation()
        except Exception as exc:
            self.record(name, 'FAIL', str(exc))
            raise
        self.record(name, 'PASS', detail)
        return detail

    def spawn(self, command, log_name, timeout=None):
        stream = (self.output / log_name).open('w', buffering=1)
        self.logs.append(stream)
        proc = pexpect.spawn(command[0], command[1:], encoding='utf-8', codec_errors='replace',
                             timeout=timeout or self.args.timeout, echo=False, dimensions=(40, 160))
        proc.delaybeforesend = None
        # Never log sent passwords. Only output from the emulated serial/SSH PTY is recorded.
        proc.logfile_read = stream
        return proc

    def sendline(self, proc, text):
        # Xen's emulated UART input ring can drop a long burst under TCG.
        # Pace input in small chunks, including the command-result envelope.
        for offset in range(0, len(text), 32):
            proc.send(text[offset:offset + 32])
            time.sleep(0.03)
        proc.send('\r')

    def shell(self, proc, domain):
        prompt = r'(?m)^[^\r\n]*[#$][ \t]*$'
        if not self.args.manual_login:
            # The validation images use agetty --autologin root. The text
            # "login: root (automatic login)" must not cause an extra username.
            proc.expect(prompt)
        else:
            for _ in range(8):
                found = proc.expect([prompt, r'(?m)^[^\r\n]*login:[ \t]*$', r'(?i)Password:[ \t]*$'])
                if found == 0:
                    break
                if found == 1:
                    self.sendline(proc, 'root')
                else:
                    if not self.args.password_file:
                        raise RuntimeError(f'{domain} requested a password but --password-file is absent')
                    self.sendline(proc, Path(self.args.password_file).read_text().strip())
            else:
                raise RuntimeError(f'Could not enter {domain} shell')
        self.prompts[id(proc)] = f'__{domain.upper()}_PROMPT__# '
        self.command(proc, f"stty -echo -onlcr; export PS1='__{domain.upper()}_PROMPT__# '; id -u",
                     contains=r'(?m)^0$')
        return f'{domain} root shell reached on a real console'

    def command(self, proc, command, contains=None, timeout=None):
        marker = '__RC_' + uuid.uuid4().hex[:12] + '_'
        self.sendline(proc, f"{{ {command}; }}; result=$?; printf '\\n{marker}%s__\\n' \"$result\"")
        proc.expect(r'(?m)^' + re.escape(marker) + r'(\d+)__\r*$', timeout=timeout or self.args.timeout)
        # Keep raw PTY bytes in serial.log, but remove terminal control
        # sequences from the textual values being asserted (bash bracketed
        # paste emits CSI ?2004l immediately before the first command output).
        output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', proc.before.replace('\r', ''))
        code = int(proc.match.group(1))
        # Consume the prompt belonging to this command. Leaving an old Dom0
        # prompt buffered could otherwise be mistaken for a newly booted guest.
        proc.expect_exact(self.prompts[id(proc)], timeout=timeout or self.args.timeout)
        self.report['commands'].append({'console': self.prompts[id(proc)], 'command': command,
                                        'exit_code': code, 'output': output.strip()})
        if code:
            raise RuntimeError(f'Guest command failed ({code}): {command}\n{output[-6000:]}')
        if contains and not re.search(contains, output):
            raise RuntimeError(f'Expected output {contains!r} absent for {command}\n{output[-6000:]}')
        return output.strip()

    def detach(self):
        # Xen's console client recognizes the escape only when read() returns
        # this one byte. Appending Enter can coalesce both bytes and forward
        # them into the guest instead of detaching.
        self.serial.send('\x1d')
        self.serial.expect_exact('__DOM0_PROMPT__# ')
        self.prompts[id(self.serial)] = '__DOM0_PROMPT__# '

    def boot(self):
        args = self.args
        for name in ['xen', 'kernel', 'rootfs', 'initrd']:
            value = getattr(args, name)
            if not value:
                continue
            path = Path(value).resolve()
            if not path.is_file():
                raise RuntimeError(f'Missing {name}: {path}')
            self.report['artifacts'][name] = {'path': str(path), 'bytes': path.stat().st_size,
                                               'sha256': digest(path)}
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', args.ssh_port))
            port = sock.getsockname()[1]
        self.ssh_port = port
        dtb = self.output / 'xen.dtb'
        dtb_cmd = [sys.executable, str(Path(__file__).with_name('make-dtb.py')),
                   '--qemu', args.qemu, '--kernel', str(Path(args.kernel).resolve()),
                   '--output', str(dtb), '--memory', str(args.memory), '--cpus', str(args.cpus),
                   '--cpu', args.cpu, '--dom0-memory', str(args.dom0_memory)]
        if args.initrd:
            dtb_cmd += ['--initrd', str(Path(args.initrd).resolve())]
        subprocess.run(dtb_cmd, check=True)
        command = [args.qemu, '-machine', 'virt,gic-version=3,virtualization=on',
                   '-accel', 'tcg', '-cpu', args.cpu, '-smp', str(args.cpus),
                   '-m', str(args.memory), '-display', 'none', '-monitor', 'none',
                   '-serial', 'stdio', '-no-reboot', '-snapshot',
                   '-kernel', str(Path(args.xen).resolve()), '-dtb', str(dtb),
                   '-device', f'loader,file={Path(args.kernel).resolve()},addr=0x45000000',
                   '-drive', f'if=none,id=dom0,format=raw,file={Path(args.rootfs).resolve()}',
                   '-device', 'virtio-blk-device,drive=dom0',
                   '-netdev', f'user,id=net0,hostfwd=tcp:127.0.0.1:{port}-:22',
                   '-device', 'virtio-net-device,netdev=net0']
        if args.initrd:
            command += ['-device', f'loader,file={Path(args.initrd).resolve()},addr=0x50000000']
        self.report['qemu_command'] = command
        self.report['qemu_version'] = subprocess.check_output([args.qemu, '--version'], text=True).splitlines()[0]
        self.save()
        self.serial = self.spawn(command, 'serial.log')
        self.serial.expect(r'Xen version 4\.19\.0')
        self.record('xen_banner', 'PASS', 'Xen 4.19.0 banner observed from emulated ARM execution')
        return self.shell(self.serial, 'dom0')

    def toolstack(self):
        if self.args.prepare_command:
            self.command(self.serial, self.args.prepare_command)
        info = self.command(self.serial, 'xl info', contains=r'xen_version\s*:\s*4\.19\.0')
        listing = self.command(self.serial, 'xl list')
        if not re.search(r'(?m)^Domain-0\s+0\s', listing) or re.search(r'(?m)^guest1\s', listing):
            raise RuntimeError('Expected only Domain-0 before manual guest creation: ' + listing)
        self.command(self.serial, 'xl dmesg', contains=r'Xen version 4\.19\.0')
        self.command(self.serial, 'test -s /etc/xen/guest1.cfg && test -x /usr/sbin/guest1-start')
        return {'xl_info': info, 'initial_domains': listing}

    def create_guest(self, repeat=False):
        self.sendline(self.serial, 'guest1-start --console')
        self.shell(self.serial, 'guest1')
        self.command(self.serial, 'hostname', contains=r'(?m)^guest1\r?$')
        self.command(self.serial, 'uname -m', contains=r'(?m)^aarch64\r?$')
        if repeat:
            self.command(self.serial, "test -s /root/qemu-write-test && cat /root/qemu-write-test",
                         contains='qemu-rootfs-write-ok')
        else:
            self.command(self.serial, "printf 'qemu-rootfs-write-ok\\n' > /root/qemu-write-test; sync; cat /root/qemu-write-test",
                         contains='qemu-rootfs-write-ok')
        self.detach()
        listing = self.command(self.serial, 'xl list')
        if not re.search(r'(?m)^guest1\s+[1-9][0-9]*\s', listing):
            raise RuntimeError('guest1 missing after console detach: ' + listing)
        return {'guest_shell': 'aarch64 root shell with writable rootfs', 'domains': listing,
                'persisted_file_after_recreate': repeat}

    def ssh_console(self):
        key = Path(self.args.ssh_key).resolve()
        if not key.is_file():
            raise RuntimeError(f'SSH private key missing: {key}')
        key.chmod(0o600)
        command = ['ssh', '-tt', '-p', str(self.ssh_port), '-i', str(key),
                   '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                   '-o', 'StrictHostKeyChecking=accept-new',
                   '-o', f'UserKnownHostsFile={self.output / "known_hosts"}',
                   '-o', 'ConnectTimeout=15', 'root@127.0.0.1',
                   "printf '__DOM0_SSH_CONNECTED__\\n'; exec xl console guest1"]
        self.console = self.spawn(command, 'ssh-guest-console.log')
        self.console.expect(r'(?m)^__DOM0_SSH_CONNECTED__\r*$')
        self.sendline(self.console, '')
        self.shell(self.console, 'guest1')
        return 'Public-key SSH reached Dom0 and xl console reached the existing guest1 shell'

    def pause_resume(self):
        console = self.console
        self.command(console, 'test -x /usr/bin/guest1-counter')
        self.sendline(console, 'guest1-counter 120')
        console.expect(r'guest1 counter: (\d+)/120')
        first = int(console.match.group(1))
        before = self.command(self.serial, 'xl list -v guest1')
        paused = True
        try:
            # Xen's flags are independent: a sleeping guest can be both
            # blocked and paused (-bp---). Assert the pause flag, not a
            # scheduler state. Cleanup is armed before requesting pause.
            self.command(self.serial, 'xl pause guest1; xl list -v guest1', contains=r'\s[r-][b-]p---\s')
            # Drain bytes emitted before pause; the state check above establishes the paused state.
            stopped = first
            while True:
                # expect consumes both pexpect's existing buffer and newly
                # received bytes; read_nonblocking would ignore the former.
                found = console.expect([r'guest1 counter: (\d+)/120', pexpect.TIMEOUT], timeout=0.2)
                if found == 1:
                    break
                stopped = int(console.match.group(1))
            observed = console.expect([r'guest1 counter: (\d+)/120', pexpect.TIMEOUT], timeout=2)
            if observed != 1:
                raise RuntimeError('Guest counter output advanced while xl reported the domain paused')
            self.command(self.serial, "printf 'DOM0_ALIVE_WHILE_GUEST_PAUSED\\n'; xl list -v guest1",
                         contains=r'DOM0_ALIVE_WHILE_GUEST_PAUSED')
            self.command(self.serial, 'xl unpause guest1')
            paused = False
            console.expect(r'guest1 counter: (\d+)/120', timeout=30)
            resumed = int(console.match.group(1))
            if resumed <= stopped:
                raise RuntimeError('Counter did not continue after unpause')
            demo = self.command(self.serial, 'guest1-pause-demo 1', contains='Resumed guest1')
            after = self.command(self.serial, 'xl list -v guest1')
            old_uuid = re.findall(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', before.lower())
            new_uuid = re.findall(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', after.lower())
            if not old_uuid or old_uuid != new_uuid:
                raise RuntimeError('Guest identity changed across pause/resume')
            console.sendcontrol('c')
            console.expect_exact(self.prompts[id(console)], timeout=30)
            self.command(console, "printf 'GUEST_SHELL_AFTER_RESUME\\n'", contains='GUEST_SHELL_AFTER_RESUME')
            return {'counter_before_pause': stopped, 'counter_after_resume': resumed,
                    'same_guest_uuid': old_uuid[0], 'project_demo': demo,
                    'measurement': 'Functional pause/resume observation, not precise scheduling latency'}
        finally:
            if paused and self.serial.isalive():
                self.command(self.serial, 'xl unpause guest1')

    def shutdown_guest(self):
        self.command(self.serial, 'xl shutdown -w guest1', timeout=self.args.timeout)
        # xl -w returns on the shutdown notification, which can precede the
        # creation monitor's on_poweroff=destroy cleanup. Wait for removal;
        # never exit the interactive Dom0 shell when an assertion fails.
        self.command(self.serial,
                     'attempt=0; while xl domid guest1 >/dev/null 2>&1 && [ "$attempt" -lt 120 ]; '
                     'do attempt=$((attempt + 1)); sleep 1; done; '
                     '! xl domid guest1 >/dev/null 2>&1', timeout=self.args.timeout)
        listing = self.command(self.serial, 'xl list')
        if re.search(r'(?m)^guest1\s', listing):
            raise RuntimeError('guest1 still listed after clean shutdown: ' + listing)
        if self.console and self.console.isalive():
            self.console.expect(pexpect.EOF, timeout=30)
        return 'guest1 shut down and disappeared from the live domain list'

    def execute(self):
        exit_code = 1
        try:
            self.check('xen_and_dom0_boot', self.boot)
            self.check('dom0_toolstack', self.toolstack)
            self.check('guest1_first_boot_and_writable_root', self.create_guest)
            self.check('dom0_ssh_and_guest_console_reattach', self.ssh_console)
            self.check('guest1_pause_resume_and_project_demo', self.pause_resume)
            self.check('guest1_clean_shutdown', self.shutdown_guest)
            self.check('guest1_recreate_and_persistent_root', lambda: self.create_guest(repeat=True))
            self.check('guest1_final_shutdown', self.shutdown_guest)
            self.report['status'] = 'PASS'
            exit_code = 0
        except Exception as exc:
            self.report['error'] = str(exc)
            print('FAIL:', str(exc), file=sys.stderr, flush=True)
        finally:
            for proc in [self.console, self.serial]:
                if proc and proc.isalive():
                    proc.terminate(force=True)
            if self.serial:
                self.report['qemu_exit_status'] = self.serial.exitstatus
                self.report['qemu_signal_status'] = self.serial.signalstatus
                self.report['qemu_stop_reason'] = 'Runner cleanup after the recorded checks'
            if 'rootfs' in self.report['artifacts']:
                try:
                    base = self.report['artifacts']['rootfs']
                    after = digest(base['path'])
                    if after != base['sha256']:
                        raise RuntimeError('QEMU changed the source Dom0 disk image')
                    self.record('source_disk_unchanged', 'PASS', {'sha256_before_and_after': after})
                except Exception as exc:
                    self.record('source_disk_unchanged', 'FAIL', str(exc))
                    self.report['status'] = 'FAIL'
                    exit_code = 1
            for stream in self.logs:
                stream.close()
            self.report['finished_at'] = datetime.now(timezone.utc).isoformat()
            self.save()
            print('Report:', self.output / 'report.json', flush=True)
        return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', default='qemu-system-aarch64')
    parser.add_argument('--xen', default=str(ROOT / 'local/qemu/xen'))
    parser.add_argument('--kernel', default=str(ROOT / 'local/qemu/Image'))
    parser.add_argument('--initrd', default=str(ROOT / 'local/qemu/initrd.img'))
    parser.add_argument('--rootfs', default=str(ROOT / 'local/qemu/dom0.ext4'))
    parser.add_argument('--ssh-key', default=str(ROOT / 'local/credentials/id_ed25519'))
    parser.add_argument('--password-file', default=str(ROOT / 'local/credentials/root-password.txt'))
    parser.add_argument('--manual-login', action='store_true', help='Use login/password prompts instead of the validation images\' root autologin')
    parser.add_argument('--ssh-port', type=int, default=0)
    parser.add_argument('--memory', type=int, default=1536)
    parser.add_argument('--dom0-memory', type=int, default=512)
    parser.add_argument('--cpus', type=int, default=2)
    parser.add_argument('--cpu', default='cortex-a57')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--prepare-command', default='systemctl start qemu-xen.service && systemctl is-active --quiet qemu-xen.service')
    parser.add_argument('--output', default=str(ROOT / 'local/qemu/results' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    args = parser.parse_args()
    return Runner(args).execute()


if __name__ == '__main__':
    sys.exit(main())
