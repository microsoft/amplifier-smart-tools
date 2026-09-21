#!/usr/bin/env python3
"""Copy this version of the shared theme into explicitly selected checkouts."""
import argparse
import shutil
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('checkouts', nargs='+', type=Path)
args = parser.parse_args()
source = Path(__file__).resolve().parent/'theme'
for checkout in args.checkouts:
    root = checkout.resolve()
    if not (root/'site/site.json').is_file():
        parser.error(f'{root} is not a configured Smart Tools website')
    target = root/'site/theme'
    if target == source:
        continue
    for name in ('build.py', 'style.css', 'site.js', 'family.json', 'LICENSE'):
        target.mkdir(exist_ok=True)
        shutil.copy2(source/name, target/name)
    if (source/'assets').is_dir():
        shutil.copytree(source/'assets', target/'assets', dirs_exist_ok=True)
    print(f'Updated {target}')
