import setuptools
import subprocess
import os

cfbs_version = subprocess.run(['git', 'describe', '--tags'], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()
assert "." in cfbs_version

assert os.path.isfile("cfbs/version.py")
with open("cfbs/VERSION", "w", encoding="utf-8") as fh:
    fh.write(f"{cfbs_version}\n")

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
    url="https://github.com/olehermanse/cfbs",
    packages=setuptools.find_packages(),
    package_data={'cfbs': ['VERSION']},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "cfbs = cfbs.main:main"
        ]
    },
    install_requires=[
      "requests >= 2.25.1",
    ],
)
