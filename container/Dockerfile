FROM osrf/ros:melodic-desktop-full

# Adding keys for ROS
RUN sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
RUN apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

#all the apt installs
RUN apt update &&  apt install -y expect wget git nano ssh python-pip libasound2 libgtk-3-0 libignition-math2-dev libgazebo9-dev xvfb libavdevice-dev libavfilter-dev libopus-dev libvpx-dev pkg-config python3-pip python3-yaml python-catkin-tools python3-dev python3-numpy libsrtp2-dev && rm -rf /var/lib/apt/lists/*

#python installs
RUN pip install mavproxy pymavlink
#recent versions of aiortc and its dependency av cause problems
RUN pip3 install rospkg catkin_pkg aiohttp aiortc==0.9.22 opencv-python aiohttp_cors dronekit

#[ardupilot]: clone and build ardupilot
WORKDIR /home
RUN git clone --recurse-submodules -j8 https://github.com/ArduPilot/ardupilot.git
WORKDIR /home/ardupilot
RUN sed -i 's/sudo//g' Tools/environment_install/install-prereqs-ubuntu.sh > Tools/environment_install/install-prereqs-ubuntu.sh
RUN useradd --no-log-init -r notroot
USER notroot
#cant be run as root
RUN USER=nobody Tools/environment_install/install-prereqs-ubuntu.sh -y
USER root
RUN ./waf configure --board sitl
RUN ./waf copter

#[sitl]: clone and build
WORKDIR /home
RUN git clone https://github.com/khancyr/ardupilot_gazebo
WORKDIR /home/ardupilot_gazebo
RUN git checkout remotes/origin/dev
RUN mkdir build
WORKDIR /home/ardupilot_gazebo/build
RUN cmake ..
RUN make -j4
RUN make install

#[cv_bridge]: set up for python 3
WORKDIR /home
RUN mkdir -p py3_cv_bridge_ws/src
WORKDIR /home/py3_cv_bridge_ws
RUN /bin/bash -c '. /opt/ros/melodic/setup.bash && catkin config -DPYTHON_EXECUTABLE=/usr/bin/python3 -DPYTHON_INCLUDE_DIR=/usr/include/python3.6m -DPYTHON_LIBRARY=/usr/lib/x86_64-linux-gnu/libpython3.6m.so && catkin config --install'
WORKDIR /home/py3_cv_bridge_ws/src
RUN git clone -b melodic https://github.com/ros-perception/vision_opencv.git
WORKDIR  /home/py3_cv_bridge_ws
RUN /bin/bash -c '. /opt/ros/melodic/setup.bash && catkin build cv_bridge'

#copy gazebo resources and files
COPY models /models
COPY worlds /worlds
COPY gimbal_small_2d /models/gimbal_small_2d
COPY pyrtc_ros.py /home/pyrtc_ros/pyrtc_ros.py
COPY client.js /home/pyrtc_ros/client.js
COPY index.html /home/pyrtc_ros/index.html

COPY nipple.js /home/pyrtc_ros/nipple.js
COPY collection.js /home/pyrtc_ros/collection.js
COPY index.js /home/pyrtc_ros/index.js
COPY manager.js /home/pyrtc_ros/manager.js
COPY super.js /home/pyrtc_ros/super.js
COPY utils.js /home/pyrtc_ros/utils.js

COPY gauge.js /home/pyrtc_ros/gauge.js

WORKDIR /home
COPY start /home

EXPOSE 8080
ENTRYPOINT [ "./start" ]
