# -*- coding: utf-8 -*-
from pathlib import Path
from setuptools import setup, find_packages

def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [str(path.parent) for path in Path(package).glob("**/__init__.py")]

try:
    long_description = open("README.rst").read()
except IOError:
    long_description = "A GUI for yt-dlp that aims to simplify its usage"

setup(
    name="video-dl",
    version="1.0.9a",
    description="yt-dlp",
    long_description=long_description,
    license="MIT",
    author="Kenshin9977",
    author_email="unknown",
    url="https://github.com/Kenshin9977/video-dl",
    packages=['', 'utils', 'components_handlers', 'updater'],
    package_data={'': ['*.ini', '*.ico', '*.png', '*.txt', '*.in', '*.md']},
    python_requires='>=3.10',
    install_requires=[
    	'boto3',
	'black',
	'darkdetect',
	'environs',
	'fire',
	'flake8',
	'flet>=0.3.0.dev968',
	'gputil',
	'mergedeep',
	'pillow',
	'pyinstaller',
	'pynacl',
	'quantiphy',
	'requests',
	'tomlkit',
	'yt-dlp',
	],
    entry_points={"console_scripts": ["video-dl=app:main"]},
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
    ]
)
