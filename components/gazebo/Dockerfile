ARG GAZEBO_VERSION="jetty"
FROM ghcr.io/cpslab-asu/multicosim/gazebo:${GAZEBO_VERSION}

LABEL org.opencontainers.image.source=https://github.com/cpslab-asu/multicosim-demo-rover
LABEL org.opencontainers.image.description="Gazebo image for MultiCoSim rover example"
LABEL org.opencontainers.image.license=BSD-3-Clause

COPY ./resources/ /app/resources/

ENV GZ_SIM_RESOURCE_PATH=/app/resources/models${GZ_SIM_RESOURCE_PATH:+":$GZ_SIM_RESOURCE_PATH"}
