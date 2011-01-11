from distutils.core import setup
import os
import subprocess


def get_version():
    proc = subprocess.Popen(
        ["dpkg-parsechangelog"],
        cwd=os.path.abspath(os.path.dirname(__file__)),
        stdout=subprocess.PIPE)
    output, _ = proc.communicate()
    version = None
    for line in output.split("\n"):
        if line.startswith("Version: "):
            version = line.split(" ", 1)[1].strip()
    assert version is not None, (
        "Couldn't determine version number from debian changelog")


setup(
        name="hwpack",
        version=get_version(),
        packages=["hwpack", "linaro_media_create"],
     )
