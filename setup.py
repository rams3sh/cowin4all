import setuptools

from cowin4all.utils import get_platform

platform = get_platform()

with open('requirements.txt') as f:
    required = f.read().splitlines()

if platform == "android":
    not_required = ["uvicorn", "fastapi"]
    temp = []
    for r in required:
        for n in not_required:
            if r.startswith(n):
                required.remove(r)
    required = temp

version = "0.0"

setuptools.setup(
    name="cowin4all",
    author="rams3sh",
    description="Python App and SDK for developing CoWIN slot booking",
    version=version,
    packages=["cowin4all", "cowin4all_sdk"],
    install_requires=required,
    include_package_data=True,
    entry_points={'console_scripts': ['cowin4all=app:main']},
    python_requires='>=3.8',)
