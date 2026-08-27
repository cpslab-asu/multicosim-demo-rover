FROM base AS fetch

# Install curl to download ROS2 package
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y curl

# Download the proper ROS2 debian package from GitHub releases
RUN <<EOF
    export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
    export OS_NAME=$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})
    curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${OS_NAME}_all.deb"
EOF

FROM base AS final

RUN --mount=from=fetch,source=/tmp,target=/tmp dpkg -i /tmp/ros2-apt-source.deb

# We install ros-jazzy-actuator-msgs here because that is how ROSDEP will want
# to install it later after we have deleted the package indices
ARG ROS2_VERSION="lyrical"
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y  \
        python3 \
        python3-pip \
        python3-rosdep \
        ros-${ROS2_VERSION}-ros-base \
        ros-${ROS2_VERSION}-actuator-msgs \
        ros-${ROS2_VERSION}-message-filters \
        ros-${ROS2_VERSION}-ros-gz-interfaces \
        ros-dev-tools && \
    rm -rf /var/lib/apt/lists/* \
    ;

RUN --mount=from=pkgs,target=/pkgs \
    python3 -m pip install --break-system-packages /pkgs/roverctl /pkgs/multicosim

# Install ROS2 dependencies
RUN --mount=source=./rover_ws,target=/rover_ws <<EOF
#!/bin/bash
cd /rover_ws
source /opt/ros/${ROS2_VERSION}/setup.bash
rosdep init
rosdep update
rosdep install -y --from-paths src
EOF

COPY <<EOF /root/.bashrc
source /opt/ros/${ROS2_VERSION}/setup.bash
EOF

WORKDIR /rover_ws

COPY ./rover_ws/ ./

# Build rover_node package using colcon
RUN <<EOF
    #!/bin/bash
    source /opt/ros/${ROS2_VERSION}/setup.bash
    colcon build --packages-select rover_node
EOF

COPY --chmod=+x ./controller.sh /usr/local/bin/
ENV ROS2_VERSION="${ROS2_VERSION}"

CMD ["controller.sh"]
