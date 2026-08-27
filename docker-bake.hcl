group "default" {
  targets = ["components"]
}

group "components" {
  targets = ["controller", "bridge", "gazebo"]
}

variable "ROS2_VERSION" {
  default = "rolling"
}

target "controller" {
  context = "./components/controller"
  contexts = {
    base = "docker-image://ubuntu:26.04"
    pkgs = "./packages"
  }
  args = {
    ROS2_VERSION = ROS2_VERSION
  }
  tags = [
    "ghcr.io/cpslab-asu/multicosim-demo-rover/controller:${ROS2_VERSION}",
  ]
}

target "bridge" {
  context = "./components/bridge"
  args = {
    ROS2_VERSION = ROS2_VERSION
  }
  tags = [
    "ghcr.io/cpslab-asu/multicosim-demo-rover/bridge:${ROS2_VERSION}"
  ]
}

variable "GAZEBO_VERSION" {
  default = "rotary"
}

target "gazebo" {
  context = "./components/gazebo"
  args = {
    GAZEBO_VERSION = GAZEBO_VERSION
  }
  tags = [
    "ghcr.io/cpslab-asu/multicosim-demo-rover/gazebo:${GAZEBO_VERSION}"
  ]
}
