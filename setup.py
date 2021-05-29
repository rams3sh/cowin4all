import setuptools
import sys
import subprocess


def get_platform():
    platform = sys.platform
    if platform in ('win32', 'cygwin'):
        return 'windows'
    elif platform == 'darwin':
        return 'macosx'
    elif platform.startswith('linux'):
        path = str(subprocess.check_output('which python3', shell=True))
        if "com.termux" in path:
            return "android"
        else:
            return "linux"
    elif platform.startswith('freebsd'):
        return 'linux'
    return 'unknown'


operating_system = get_platform()

with open('requirements.txt') as f:
    required = [p.strip() for p in f.read().splitlines() if not p.startswith("#")]

if operating_system == "linux":
    not_required = ["uvicorn", "fastapi"]
    temp = []
    for r in required:
        if any([n for n in not_required if r.startswith(n)]):
            continue
        else:
            temp.append(r)
    required = temp

version = "0.0"


setuptools.setup(
    name="cowin4all",
    author="rams3sh",
    description="Python App and SDK for developing CoWIN slot booking",
    version=version,
    packages=["cowin4all", "cowin4all.cowin4all_sdk", "cowin4all.otp_plugins"],
    install_requires=required,
    include_package_data=True,
    entry_points={'console_scripts': ['cowin4all=cowin4all.app:main']},
    python_requires='>=3.8'
    )
