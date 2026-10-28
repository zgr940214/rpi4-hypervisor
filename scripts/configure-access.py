#!/usr/bin/env python3
"""Create local lab credentials once; never print secret material."""
import os
import pathlib
import secrets
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    os.umask(0o077)
    credentials = ROOT / "local/credentials"
    generated = ROOT / "local/generated"
    credentials.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    key = credentials / "id_ed25519"
    if not key.exists():
        if key.with_suffix(".pub").exists():
            raise SystemExit("Public key already exists without its private key; refusing replacement")
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C",
                        "pi4-xen-lab", "-f", str(key)], check=True)
    if not key.with_suffix(".pub").exists():
        raise SystemExit("Existing private key has no public key; restore the matching public key")
    # Git restores regular files as 0644; OpenSSH requires a private key to be 0600.
    key.chmod(0o600)
    derived = subprocess.check_output(
        ["ssh-keygen", "-y", "-P", "", "-f", str(key)], text=True).split()
    if derived[:2] != key.with_suffix(".pub").read_text().split()[:2]:
        raise SystemExit("Existing public and private SSH keys do not match; refusing replacement")
    password = credentials / "root-password.txt"
    hashfile = credentials / "root-password.sha512"
    if password.exists() != hashfile.exists():
        raise SystemExit("Password and hash must both exist or both be absent; restore the matching pair")
    if not password.exists():
        password.write_text(secrets.token_urlsafe(24) + "\n")
        result = subprocess.run(["openssl", "passwd", "-6", "-stdin"],
                                input=password.read_text(), text=True,
                                capture_output=True, check=True)
        hashfile.write_text(result.stdout)
    stored_hash = hashfile.read_text().strip()
    fields = stored_hash.split("$")
    if len(fields) != 4 or fields[1] != "6":
        raise SystemExit("Unsupported stored password hash; expected SHA512-crypt")
    verified = subprocess.run(["openssl", "passwd", "-6", "-salt", fields[2], "-stdin"],
                              input=password.read_text(), text=True,
                              capture_output=True, check=True).stdout.strip()
    if verified != stored_hash:
        raise SystemExit("Existing password and hash do not match; refusing replacement")
    for p in credentials.iterdir():
        if p.is_file():
            p.chmod(0o600)
    # The escape protects dollar signs when extrausers invokes the shell.
    password_hash = hashfile.read_text().strip().replace("$", "\\$")
    content = ('PI4_XEN_ACCESS_DIR = "/work/local/credentials"\n'
               f'PI4_XEN_ROOT_PASSWORD_HASH = "{password_hash}"\n')
    target = generated / "access.inc"
    if not target.exists() or target.read_text() != content:
        target.write_text(content)
    print("Lab credentials are in local/credentials/ (contents not logged).")


if __name__ == "__main__":
    main()
