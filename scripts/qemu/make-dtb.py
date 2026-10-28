#!/usr/bin/env python3
"""Generate a Xen-aware DTB from the same QEMU virt machine being tested."""
import argparse
import json
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.run(list(map(str, args)), check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def create(args):
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    kernel = Path(args.kernel).resolve()
    if not kernel.is_file() or not kernel.stat().st_size:
        raise ValueError("Dom0 kernel is missing or empty")
    kernel_address = int(args.kernel_address, 0)
    initrd_address = int(args.initrd_address, 0)
    memory_end = 0x40000000 + args.memory * 1024 * 1024
    if kernel_address + kernel.stat().st_size >= initrd_address:
        raise ValueError("Dom0 kernel overlaps the initramfs load address")
    base = output.with_suffix('.base.dtb')
    command = [args.qemu, '-machine', f'virt,gic-version=3,virtualization=on,dumpdtb={base}',
               '-cpu', args.cpu, '-smp', str(args.cpus), '-m', str(args.memory),
               '-display', 'none', '-serial', 'none', '-monitor', 'none', '-nic', 'none']
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    output.write_bytes(base.read_bytes())
    uart = run('fdtget', '-t', 's', output, '/chosen', 'stdout-path').split(':')[0]
    xen_args = (f'console=dtuart dtuart={uart} dom0_mem={args.dom0_memory}M,max:{args.dom0_memory}M '
                f'dom0_max_vcpus={args.cpus} loglvl=info guest_loglvl=info')
    run('fdtput', '-t', 's', output, '/chosen', 'xen,xen-bootargs', xen_args)
    run('fdtput', '-t', 's', output, '/chosen', 'xen,dom0-bootargs', args.dom0_args)
    run('fdtput', '-t', 'x', output, '/chosen', '#address-cells', '1')
    run('fdtput', '-t', 'x', output, '/chosen', '#size-cells', '1')
    modules = []
    for kind, address, path in [('kernel', kernel_address, kernel),
                                 ('ramdisk', initrd_address, Path(args.initrd).resolve() if args.initrd else None)]:
        if path is None:
            continue
        size = path.stat().st_size
        if not size or address < 0x40000000 or address + size >= memory_end:
            raise ValueError(f'{kind} lies outside the configured RAM window')
        node = f'/chosen/module@{address:x}'
        run('fdtput', '-c', output, node)
        run('fdtput', '-t', 's', output, node, 'compatible', f'multiboot,{kind}', 'multiboot,module')
        run('fdtput', '-t', 'x', output, node, 'reg', f'{address:x}', f'{size:x}')
        modules.append({'kind': kind, 'path': str(path), 'address': address, 'size': size})
    run('dtc', '-I', 'dtb', '-O', 'dts', '-o', output.with_suffix('.dts'), output)
    info = {'qemu_dump_command': command, 'uart': uart, 'xen_args': xen_args,
            'dom0_args': args.dom0_args, 'modules': modules}
    output.with_suffix('.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', default='qemu-system-aarch64')
    parser.add_argument('--kernel', required=True)
    parser.add_argument('--initrd')
    parser.add_argument('--output', required=True)
    parser.add_argument('--cpu', default='cortex-a57')
    parser.add_argument('--cpus', type=int, default=2)
    parser.add_argument('--memory', type=int, default=1536)
    parser.add_argument('--dom0-memory', type=int, default=512)
    parser.add_argument('--kernel-address', default='0x45000000')
    parser.add_argument('--initrd-address', default='0x50000000')
    parser.add_argument('--dom0-args', default='console=hvc0 earlycon=xenboot root=/dev/vda rw rootwait net.ifnames=0')
    create(parser.parse_args())


if __name__ == '__main__':
    main()
