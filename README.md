The purpose of this repo is to demonstrate the possibility of flying a drone from a browser using the [WebRTC](https://webrtc.org/) protocol. WebRTC allows for low-latency, peer-to-peer streaming of video and arbitrary data, making it perfect for such a use case. 

Pull the Docker image `andremyers/drones:latest` and run with `docker run -p 8080:8080 -it andremyers/drones:latest`. Visit `localhost:8080` in your browser (Firefox may encounter problems). You should see this:

![Alt Text](https://github.com/pbafff/DroneRTC/raw/master/Peek%202020-07-21%2021-15.gif)

Fly the drone using W and S to control thrust, i.e. altitude; A and D to control roll; and the on-screen joystick to control pitch and yaw. The drone is running ArduCopter in Loiter mode for easy flying. It is simulated in [Gazebo](http://gazebosim.org/).

Run this container on a vm (with a GPU attached) to see how well WebRTC handles latency! In my own informal tests I was able to easily fly the drone from NYC while running the container on a northern Virginia Google Cloud vm. 

TODO:
Figure out how to actually obtain and display the exact amount of latency.
