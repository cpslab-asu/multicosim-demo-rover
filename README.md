# MultiCoSim Rover Demo

This repository implements a rover system using ROS2 nodes and demonstrates how a simulation would
be configured.

## System Requirements

This project is developed using [`pixi`](https://pixi.prefix.dev) which is a dependency management
tool built on top of the Conda ecosystem. However, unlike Conda, `pixi` installs dependencies
locally to the project, making it much nicer to interact with. All the project and development
dependencies will be installed and managed by `pixi`.

This project uses [Docker](https//docker.com) to manage the simulation components. Please ensure
that you have installed the Docker daemon.

For convenience, this project also provides a `.envrc` file that can be automatically activated
when you enter the project directory using [direnv](https://direnv.net). This is optional, but
exports several helpful environment variables that will otherwise need to be manually set.

## Building the Images

Building the images for this project consists of two steps. We use Docker
[bake](https://docs.docker.com/build/bake/) to manage the build process, which is configured through
the `docker-bake.hcl` file. If you are *not* using direnv, you will need to either export the
build configuration environment variables once before running these commands, or prefix each command
with the environment variable definitions like so:

```sh
# Option 1
export ROS_VERSION="lyrical"
export GAZEBO_VERSION="jetty"
cmd

# Option 2
ROS_VERSION="lyrical" GAZEBO_VERSION="jetty" cmd
```

The first step is to build the base containers, which should be done from the `packages/multicosim`
directory with the following command:

```sh
docker buildx bake gazebo
```

The second step is to build the rover-specific images. From the project root, run the command:

```sh
docker buildx bake
```

This should produce 3 images: 

  - `ghcr.io/cpslab-asu/multicosim-demo-rover/controller:lyrical`
  - `ghcr.io/cpslab-asu/multicosim-demo-rover/bridge:lyrical`
  - `ghcr.io/cpslab-asu/multicosim-demo-rover/gazebo:jetty`

## Running the Simulation

The simulation is executed using the `src/rover.py` script. If you are using direnv, then the pixi
environment should already be active for you and you can run the script with the command:

```sh
python3 src/rover.py
```

If you are not using direnv, or want to use a direnv-agnostic command, you can prefix this command
with `pixi run` to ensure that it is executed in the pixi environment.

```sh
pixi run python3 src/rover.py
```
