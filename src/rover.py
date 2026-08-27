from __future__ import annotations

import asyncio
import logging
import os
import time
import typing

import attrs
import multicosim.containers
import multicosim.gazebo as gz
import namer
import numpy.random as rand

from roverctl.attacks import FixedSpeed, GaussianMagnet
from roverctl.messages import Result, Start

CONTROLLER_SERVER_PORT: typing.Final[int] = 5556
GAZEBO_VERSION: typing.Final[str] = os.environ.get("GAZEBO_VERSION", "jetty")
ROS2_VERSION: typing.Final[str] = os.environ.get("ROS2_VERSION", "lyrical")


@attrs.frozen()
class Gazebo(multicosim.containers.Gazebo):
    group: str = attrs.field(kw_only=True)

    @typing.override
    def to_options(self) -> multicosim.containers.ContainerOptions:
        options = super().to_options()
        options.name = f"{self.group}-gazebo"
        return options


@attrs.frozen()
class Bridge(multicosim.containers.Component):
    group: str = attrs.field(kw_only=True)

    @typing.override
    def to_options(self) -> multicosim.containers.ContainerOptions:
        options = super().to_options()
        options.name = f"{self.group}-bridge"
        return options


@attrs.frozen()
class Controller(multicosim.containers.ConnectedComponent[Start, Result]):
    msg_type: type[Start] = attrs.field(init=False, default=Start)
    data_type: type[Result] = attrs.field(init=False, default=Result)
    group: str = attrs.field(kw_only=True)

    @typing.override
    def to_options(self) -> multicosim.containers.ContainerOptions:
        options = super().to_options()
        options.name = f"{self.group}-controller"
        return options


def simulate(backend: gz.Backend):
    group: str = namer.generate().replace("-", "_")
    gazebo = Gazebo(
        image=f"ghcr.io/cpslab-asu/mff-demo-rover/gazebo:{GAZEBO_VERSION}",
        template="/app/resources/worlds/rover.sdf",
        options=gz.Options(
            world=group,
            backend=backend,
            step_size=0.001,
            run=False,
        ),
        group=group,
    )

    bridge = Bridge(
        image=f"ghcr.io/cpslab-asu/mff-demo-rover/bridge:{ROS2_VERSION}",
        command=f"bridge.sh {gazebo.options.world}",
        group=group,
    )

    controller = Controller(
        image=f"ghcr.io/cpslab-asu/mff-demo-rover/controller:{ROS2_VERSION}",
        command=f"controller.sh {gazebo.options.world}",
        port=CONTROLLER_SERVER_PORT,
        tty=True,
        group=group,
    )

    sim = multicosim.containers.Simulator()
    sim.add_component(gazebo)
    sim.add_component(bridge, exit_codes={245})
    sim.add_component(controller, depends=[bridge, gazebo])

    t_start = time.time()
    logger = logging.getLogger("rover")

    with sim.run(remove="if_all_succeed") as sys:
        msg = Start(
            magnet=GaussianMagnet(4.0, 4.0, rand.default_rng(), magnitude=0.0),
            speed=FixedSpeed(magnitude=5.0),
        )

        res = asyncio.run(sys.send(controller, msg))
        duration = time.time() - t_start
        logger.info("Execution finished in %d s", duration)

    return res


if __name__ == "__main__":
    logging.basicConfig()
    simulate(gz.ODE())
