from __future__ import annotations

import logging
import math
import threading
import typing

import actuator_msgs.msg
import attrs
import geometry_msgs.msg
import message_filters
import multicosim.containers
import rclpy
import rclpy.executors
import rclpy.logging
import rclpy.node
import ros_gz_interfaces.srv
import sensor_msgs.msg
import std_msgs.msg

from roverctl import attacks, automaton, messages


class SyncronizedValue[T]:
    def __init__(self):
        self.lock: threading.Lock = threading.Lock()
        self.value: T | None = None

    def update(self, value: T) -> None:
        with self.lock:
            self.value = value

    def get(self) -> T:
        with self.lock:
            if self.value is None:
                raise RuntimeError("Synchronized value has not been updated")

            return self.value

    def is_ready(self) -> bool:
        with self.lock:
            return self.value is not None


class Time(SyncronizedValue[float]):
    @typing.override
    def update(self, value: float) -> None:
        with self.lock:
            # Only update monotonically
            if self.value is None or value > self.value:
                self.value: float | None = value


class Heading(SyncronizedValue[float]):
    pass


class Position(SyncronizedValue[tuple[float, float, float]]):
    pass


def to_heading(value: float | automaton.Heading) -> automaton.Heading:
    if isinstance(value, float):
        return automaton.Heading.unmodified(value)

    if isinstance(value, automaton.Heading):
        return value

    raise TypeError(f"Unsupported type {type(value)}, expected [float, Heading]")


@attrs.define()
class Model(automaton.Model):
    _heading: automaton.Heading = attrs.field(
        converter=to_heading,
        default=automaton.Heading.unmodified(0.0),
    )
    _position: automaton.Position = attrs.field(default=(0.0, 0.0, 0.0))

    def update(
        self, heading: float, position: automaton.Position, *, emi: float | None = None
    ) -> None:
        if emi is None:
            self._heading = automaton.Heading.unmodified(heading)
        else:
            self._heading = automaton.Heading(heading + emi, heading)

        self._position = position

    @property
    @typing.override
    def heading(self) -> automaton.Heading:
        return self._heading

    @property
    @typing.override
    def position(self) -> automaton.Position:
        return self._position


class MissionCompleted(Exception):
    def __init__(self, history: list[messages.Step]):
        super().__init__()
        self.result: messages.Result = messages.Result(history)


@typing.final
class RoverController(rclpy.node.Node):
    def __init__(self, magnet: attacks.Magnet):
        super().__init__("rover_controller")
        self.declare_parameter("world", "ngc_world")
        world = self.get_parameter("world").get_parameter_value().string_value
        self.get_logger().info(f"Configuring endpoints for Gazebo world {world}")

        period = 0.05
        self.magnet = magnet
        self.model = Model()
        self.time = Time()
        self.heading = Heading()
        self.position = Position()
        self.automaton = automaton.Automaton(self.model, period)
        self.history: list[messages.Step] = []

        self.motors_pub = self.create_publisher(
            actuator_msgs.msg.Actuators, f"/world/{world}/model/ngc_rover/command/motor_speed", 10
        )
        self.servo_pub = self.create_publisher(
            std_msgs.msg.Float64, f"/world/{world}/model/ngc_rover/servo_0", 10
        )
        self.pose_sub = message_filters.TimeSequencer(
            input_filter=message_filters.Subscriber(
                self,
                geometry_msgs.msg.PoseStamped,
                f"/world/{world}/model/ngc_rover/pose",
            ),
            delay=0.1,
            update_rate=0.01,
            queue_size=0,
            node=self,
        )
        self.magnetometer_sub = message_filters.TimeSequencer(
            input_filter=message_filters.Subscriber(
                self,
                sensor_msgs.msg.MagneticField,
                f"/world/{world}/model/ngc_rover/magnetometer",
            ),
            delay=0.1,
            update_rate=0.01,
            queue_size=0,
            node=self,
        )
        self.timer = self.create_timer(period, self.update_automaton, autostart=False)
        self.sync = message_filters.TimeSynchronizer([self.pose_sub, self.magnetometer_sub], 10)
        self.sync.registerCallback(self.sync_state)

        self.client = self.create_client(ros_gz_interfaces.srv.ControlWorld, f"/world/{world}/control")

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for world control service to be available...", once=True)

        self.get_logger().info("Sending request to start simulation")

        start_req = ros_gz_interfaces.srv.ControlWorld.Request()
        start_req.world_control.pause = False

        self.start_resp = self.client.call_async(start_req)
        self.start_resp.add_done_callback(self.handle_start_response)

    def handle_start_response(self, response: typing.Any) -> None:
        result = response.result()
        self.get_logger().info(f"Received response {result} from control service")

        # Start control loop
        self.timer.reset()

    def sync_state(self, pose: geometry_msgs.msg.PoseStamped, mag: sensor_msgs.msg.MagneticField):
        pose_sec = pose.header.stamp.sec + pose.header.stamp.nanosec / 1e9
        mag_sec = mag.header.stamp.sec + mag.header.stamp.nanosec / 1e9

        if not self.time.is_ready() or pose_sec > self.time.get():
            x = mag.magnetic_field.x
            y = mag.magnetic_field.y

            if y > 0:
                heading: float = 90 - (math.atan(x / y) * 180 / math.pi)
            elif y < 0:
                heading = 270 - (math.atan(x / y) * 180 / math.pi)
            elif x > 0:
                heading = 180.0
            else:
                heading = 0.0

            self.time.update(pose_sec)
            self.position.update((pose.pose.position.x, pose.pose.position.y, pose.pose.position.z))
            self.heading.update(heading)
            self.get_logger().debug(
                f"State synchronized with Pose time: {pose_sec} and Magnetometer time: {mag_sec}"
            )

    def is_ready(self) -> bool:
        return self.time.is_ready() and self.heading.is_ready() and self.position.is_ready()

    def update_automaton(self) -> None:
        logger = self.get_logger()

        # Do nothing if the model has not received any data yet
        if not self.is_ready():
            logger.info("Waiting for data sources to be ready...", once=True)
            return

        logger.info("All data sources ready!", once=True)

        time = self.time.get()
        heading = self.heading.get()
        position = self.position.get()
        emi = self.magnet.offset(time, Model(heading, position))

        logger.info(f"Updating automaton -- Time: {time}")

        s1_active = isinstance(self.automaton.state, automaton.S1)
        is_stationary = all(position == step.position for step in self.history[-10:-1])

        # Only check if position is stalled when not waiting
        if not s1_active and is_stationary:
            raise RuntimeError(
                "Rover position has not changed for 10 iterations, simulation may have stalled"
            )

        self.history.append(
            messages.Step(
                time=time,
                position=position,
                heading=heading,
                roll=0.0,
                state=self.automaton.state,
            )
        )

        self.model.update(heading, position, emi=emi)
        self.automaton.step(None)

        if self.automaton.state.is_terminal():
            raise MissionCompleted(self.history)

        speed = 0.0 if self.automaton.action is automaton.Action.STOP else 8.0
        motors_msg = actuator_msgs.msg.Actuators()
        motors_msg.velocity.append(speed)

        angle = 0.5 if self.automaton.action is automaton.Action.TURN else 0.0
        servo_msg = std_msgs.msg.Float64()
        servo_msg.data = angle

        self.motors_pub.publish(motors_msg)
        self.servo_pub.publish(servo_msg)


def run(args: typing.Any = None, *, magnet: attacks.Magnet | None = None) -> messages.Result:
    rclpy.init(args=args)

    if magnet is None:
        magnet = attacks.StationaryMagnet(0.0)

    node = RoverController(magnet)
    logger = node.get_logger()
    logger.info("Received `Start` message, running mission.")

    try:
        logger.info("Spinning rover node...")
        rclpy.spin(node)
    except MissionCompleted as e:
        return e.result
    finally:
        rclpy.shutdown()

    raise RuntimeError("rover stopped spinning without being shutdown or finishing the mission")


def level_severity(levelno: int) -> rclpy.logging.LoggingSeverity:
    match levelno:
        case logging.DEBUG:
            return rclpy.logging.LoggingSeverity.DEBUG
        case logging.INFO:
            return rclpy.logging.LoggingSeverity.INFO
        case logging.WARNING:
            return rclpy.logging.LoggingSeverity.WARN
        case logging.ERROR:
            return rclpy.logging.LoggingSeverity.ERROR
        case logging.FATAL:
            return rclpy.logging.LoggingSeverity.FATAL
        case _:
            return rclpy.logging.LoggingSeverity.UNSET


class LoggerBridge(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        severity = level_severity(record.levelno)
        logger = rclpy.logging.get_logger(record.name)
        logger.log(record.msg, severity)


def listen(args: typing.Any = None):
    logging.basicConfig(level=logging.INFO, handlers=[LoggerBridge()])

    @multicosim.containers.server(msgtype=messages.Start)
    def server(msg: messages.Start) -> messages.Result:
        return run(args, magnet=msg.magnet)

    logger = rclpy.logging.get_logger("root")

    logger.info("Waiting for `Start` message...")
    server.listen(5556)


if __name__ == "__main__":
    listen()
