"""Set the clean-install root password without dropping upstream system users."""
import pathlib
import subprocess
import sys


def prepare_shadow(source, destination):
    lines = source.read_text().splitlines()
    if sum(line.startswith('root:') for line in lines) != 1:
        raise ValueError('Expected exactly one root entry in upstream shadow')
    digest = subprocess.run(['openssl', 'passwd', '-6', '-stdin'], input='password\n',
                            text=True, capture_output=True, check=True).stdout.strip()
    if not digest.startswith('$6$') or len(digest.split('$')) != 4:
        raise ValueError('OpenSSL did not produce a SHA-512 password hash')
    for index, line in enumerate(lines):
        if line.startswith('root:'):
            fields = line.split(':')
            fields[1] = digest
            lines[index] = ':'.join(fields)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(lines) + '\n')
    destination.chmod(0o600)


if __name__ == '__main__':
    prepare_shadow(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
