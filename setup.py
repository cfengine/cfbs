import setuptools
import subprocess
import os

cfbs_version = subprocess.run(['git', 'describe', '--tags'], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()
if "-" in cfbs_version:
    # when not on tag, git describe outputs: "1.3.3-22-gdf81228"
    # pip has gotten strict with version numbers
    # so change it to: "1.3.3+22.git.gdf81228"
    # See: https://peps.python.org/pep-0440/#local-version-segments
    v,i,s = cfbs_version.split("-")
    cfbs_version = v + "+" + i + ".git." + s

assert "-" not in cfbs_version
assert "." in cfbs_version

assert os.path.isfile("cfbs/version.py")
with open("cfbs/VERSION", "w", encoding="utf-8") as fh:
    fh.write("%s\n" % cfbs_version)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cfbs",
    version=cfbs_version,
    author="Northern.tech, Inc.",
    author_email="contact@northern.tech",
    description="Tooling to build, manage and deploy CFEngine policy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cfengine/cfbs",
    packages=setuptools.find_packages(),
    package_data={'cfbs': ['VERSION']},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
    entry_points={
        "console_scripts": [
            "cfbs = cfbs.main:main"
        ]
    },
    install_requires=[
    ],
)
