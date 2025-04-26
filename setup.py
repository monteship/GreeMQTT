from setuptools import setup

def get_version():
    with open("VERSION", "r") as version_file:
        return version_file.read().strip()

setup(
    name="ewe_gree_mqtt",
    version=get_version(),
    ...
)