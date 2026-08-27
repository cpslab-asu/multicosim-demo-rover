# pyright: reportUnusedCallResult=false

import glob
import os

from setuptools import setup

package_name = "rover_node"

setup(
    name=package_name,
    description="Node implementing controller for NGC Rover",
    version="0.1.0",
    license="BSD 3-Clause",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob.glob("launch/*")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    author="Quinn Thibeault",
    author_email="qthibeau@asu.edu",
    entry_points={
        "console_scripts": [
            "listen = rover_node.rover_controller:listen",
            "run = rover_node.rover_controller:run",
        ]
    },
)
