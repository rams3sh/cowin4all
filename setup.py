import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()

version = "0.0"

setuptools.setup(
    name="cowin4all",
    author="rams3sh",
    description="Python App and SDK for developing CoWIN slot booking",
    version=version,
    packages=["cowin4all", "cowin4all_sdk"],
    install_requires=required,
    include_package_data=True,
    package_data={
        "cowin4all": ["*.mp3"],
    },
    python_requires='>=3.8',)
