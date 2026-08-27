FROM ubuntu:26.04 AS fetch

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

FROM ubuntu:26.04 AS dist

RUN --mount=from=fetch,source=/tmp,target=/tmp dpkg -i /tmp/ros2-apt-source.deb

ARG ROS2_VERSION="lyrical"
RUN DEBIAN_FRONTEND=noninteractive \
    apt-get update && \
    apt-get install -y ros-${ROS2_VERSION}-ros-base ros-${ROS2_VERSION}-ros-gz-bridge && \
    rm -rf /var/lib/apt/lists/* \
    ;

COPY ./bridge-config.yaml /bridge-config.yaml
COPY --chmod=+x ./bridge.sh /usr/local/bin/bridge.sh

ENV GZ_PARTITION=multicosim
ENV ROS2_VERSION="${ROS2_VERSION}"

CMD ["bridge.sh"]
