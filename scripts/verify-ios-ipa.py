"""Check that CI produced an actual iPhone binary before publishing an artifact."""
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import zipfile


def main():
    candidates = list(Path('client/src-tauri/gen/apple').rglob('*.ipa'))
    if len(candidates) != 1:
        raise SystemExit(f'Expected one freshly built IPA, found {len(candidates)}')
    ipa = candidates[0]
    with zipfile.ZipFile(ipa) as archive:
        plists = [n for n in archive.namelist()
                  if n.startswith('Payload/') and n.count('/') == 2
                  and n.endswith('.app/Info.plist')]
        if len(plists) != 1:
            raise SystemExit('IPA must contain one app at Payload/<name>.app')
        info = plistlib.loads(archive.read(plists[0]))
        if info.get('CFBundleSupportedPlatforms') != ['iPhoneOS']:
            raise SystemExit('Build is not a physical-device iPhoneOS app')
        if not info.get('NSLocalNetworkUsageDescription'):
            raise SystemExit('Local-network permission description missing')
        executable = info.get('CFBundleExecutable', '')
        if not executable or '/' in executable:
            raise SystemExit('Invalid executable name')
        binary_name = plists[0].rsplit('/', 1)[0] + '/' + executable
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'app-binary'
            binary.write_bytes(archive.read(binary_name))
            arch = subprocess.check_output(['lipo', '-archs', str(binary)], text=True)
            if 'arm64' not in arch.split():
                raise SystemExit(f'Expected arm64, found {arch.strip()}')
    destination = Path('dist/PS5Upload-iPhone-unsigned.ipa')
    destination.parent.mkdir(exist_ok=True)
    shutil.copy2(ipa, destination)
    print(f'Validated unsigned physical-iPhone package: {destination}')
    print('Sign through Signulous. Runtime and PS5 transfer tests are still required.')


if __name__ == '__main__':
    main()
