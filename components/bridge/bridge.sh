#!/bin/bash

world="$1"

if [ -z $world ]; then
    echo "usage: bridge.sh <GAZEBO WORLD NAME>"
    exit -1
fi

echo "Bridging Gazebo world ${world}"

# Insert gazebo world name into configuration file
sed -i "s/{{GAZEBO_WORLD}}/${world}/g" /bridge-config.yaml

# Activate ROS2 environment
source /opt/ros/${ROS2_VERSION}/setup.bash

# run bridge using configuration file
exec ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=/bridge-config.yaml
