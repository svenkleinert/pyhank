import re
import subprocess
import sys
from copy import copy

VERSION_STRING = r'(\d+).(\d+).(\d+)'
SETUP_VERSION_PATTERN = re.compile(f'version="({VERSION_STRING})"')
SPECIFIER_PATTERN = re.compile(f'v?{VERSION_STRING}')


class Version:
    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self):
        return str(self.major) + '.' + str(self.minor) + '.' + str(self.patch)

    @property
    def tag(self):
        return 'v' + str(self)

    def increment_major(self):
        self.major += 1
        self.minor = 0
        self.patch = 0

    def increment_minor(self):
        self.minor += 1
        self.patch = 0

    def increment_patch(self):
        self.patch += 1


def matches_start(string: str, pattern: str):
    regex = ''.join([c+'?' for c in pattern])
    return bool(re.fullmatch(regex, string))


def main():
    with open('setup.py') as file:
        setup_info = file.read()
    version_match = SETUP_VERSION_PATTERN.search(setup_info)
    version_numbers = [int(v) for v in version_match.groups()[1:4]]
    current_version = Version(*version_numbers)
    assert str(current_version) == version_match.group(1), 'Error reading current version'
    print(f'Current version is {str(current_version)}')
    try:
        _, version = sys.argv
    except ValueError:
        version = input('Enter a version specifier [vX.Y.Z|major|minor|PATCH]: ')

    specifier_match = SPECIFIER_PATTERN.match(version)
    if specifier_match is not None:
        new_version_numbers = [int(v) for v in specifier_match.groups()[1:4]]
        new_version = Version(*new_version_numbers)
    else:
        new_version = copy(current_version)
        if matches_start(version, 'patch'):
            new_version.increment_patch()
        elif matches_start(version, 'minor'):
            new_version.increment_minor()
        elif matches_start(version, 'major'):
            new_version.increment_major()
        else:
            raise ValueError('Invalid version specifier')

    print(f'New version will be: {str(new_version)}')
    status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True)
    clean = status.stdout == b''
    do_stash = False
    if not clean:
        subprocess.run(['git', 'status'])
        stash_response = input('Working directory is not clean. '
                               'Do you want to continue with current status, or stash [c/S]?: ')
        do_stash = not stash_response.lower().startswith('c')
        if do_stash:
            print('Stashing changes')
            subprocess.run(['git', 'stash'], check=True)
    # edit file
    setup_info = SETUP_VERSION_PATTERN.sub(f'version="{str(new_version)}"', setup_info)
    with open('setup.py', 'w') as file:
        file.write(setup_info)
    # commit
    subprocess.run(['git', 'add', 'setup.py'], check=True)
    subprocess.run(['git', 'commit', f'-m Set version to {str(new_version)}'], check=True)
    # tag
    message = input('Enter release message. Leave blank to use the default message):\n')
    if message == '':
        message = f'Release version {str(new_version)}'
    print(f'Using message: {message}')
    subprocess.run(['git', 'tag', '-a', '-m', message, new_version.tag], check=True)
    # push
    push_response = input('Push? [Y/n]: ')
    if not push_response.lower().startswith('n'):
        print('Pushing with tags')
        subprocess.run(['git', 'push'], check=True)
        subprocess.run(['git', 'push', '--tags'], check=True)

    if do_stash:
        print('Unstashing changes')
        subprocess.run(['git', 'stash', 'pop'])


if __name__ == '__main__':
    main()
