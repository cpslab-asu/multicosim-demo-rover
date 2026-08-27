#!/bin/bash

world="$1"

if [ -z $world ]; then
    echo "usage: controller.sh <GAZEBO WORLD NAME>" > 1
    exit 1
fi

function _term()
{
    echo "controller.sh: Received SIGTERM - Starting graceful shutdown"
    child=$!
    kill -s SIGTERM $child
    wait $child
    exit 143
}

source /opt/ros/${ROS2_VERSION}/setup.bash
source /rover_ws/install/setup.bash

trap _term SIGTERM
ros2 run rover_node listen --ros-args -p world:="$1" &
wait $!
