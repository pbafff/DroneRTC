#!/usr/bin/python3
import os
import sys
import uuid
import json
import asyncio
import argparse
import subprocess

import rospy
import roslib
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from dronekit import connect, VehicleMode

import aiohttp_cors
from aiohttp import web
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack

pcs = set()
frame = None
io_channel = None
vehicle = None
channels = {"1": 1500, "2": 1500, "3": 1500, "4": 1500}
lat = ""
lon = ""
pitch = ""
roll = ""
yaw = ""
groundspeed = ""
heading = ""
altitude = ""


class ImageConverter:
    def __init__(self):
        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber(
            "/iris/camera1/image_raw", Image, self.callback
        )

    def callback(self, data):
        try:
            global frame
            frame = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            print(e)


class VideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        global frame
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame


async def connectToDrone(app):
    global vehicle
    await asyncio.sleep(0.01, loop=app.loop)
    vehicle = connect("0.0.0.0:14550", wait_ready=True, heartbeat_timeout=90)

    print("Basic pre-arm checks")
    if io_channel:
        io_channel.send("init Basic pre-arm checks")

    while not vehicle.is_armable:
        print("Waiting for vehicle to initialize...")
        if io_channel:
            io_channel.send("init Waiting for vehicle to initialize...")
        await asyncio.sleep(1, loop=app.loop)

    print("Arming motors")
    if io_channel:
        io_channel.send("init Arming motors")

    vehicle.mode = VehicleMode("LOITER")
    vehicle.armed = True

    while not vehicle.armed:
        print("Waiting for arming...")
        if io_channel:
            io_channel.send("init Waiting for arming...")
        vehicle.armed = True
        await asyncio.sleep(1, loop=app.loop)

    print("Armed")
    if io_channel:
        io_channel.send("init Armed")

    def attribute_callback(self, name, value):
        global lat, lon, pitch, yaw, roll, groundspeed, heading, altitude
        if name == "location.global_frame":
            lat = value.lat
            lon = value.lon

        elif name == "attitude":
            pitch = round(value.pitch, 2)
            yaw = round(value.yaw, 2)
            roll = round(value.roll, 2)

        elif name == "groundspeed":
            groundspeed = round(value, 1)

        elif name == "heading":
            heading = value

        elif name == "location.global_relative_frame":
            altitude = round(value.alt, 1)

    vehicle.add_attribute_listener("location.global_frame", attribute_callback)
    vehicle.add_attribute_listener("attitude", attribute_callback)
    vehicle.add_attribute_listener("groundspeed", attribute_callback)
    vehicle.add_attribute_listener("heading", attribute_callback)
    vehicle.add_attribute_listener("location.global_relative_frame", attribute_callback)

    while vehicle.armed:
        vehicle.channels.overrides = channels
        await asyncio.sleep(0.04, loop=app.loop)


async def send_vehicle_status(app):
    await asyncio.sleep(0.01, loop=app.loop)
    while True:
        try:
            if vehicle.armed:
                io_channel.send(
                    " Lat: {}\n Lon: {}\n Pitch: {}\n Roll: {}\n Yaw: {}\n G.Spd: {}m/s Heading: {} Alt: {}m".format(
                        lat, lon, pitch, roll, yaw, groundspeed, heading, altitude
                    )
                )
        except:
            print("Vehicle status send error")
        await asyncio.sleep(0.2, loop=app.loop)


async def offer(request):
    params = await request.json()
    print("got offer request: \n" + params["sdp"])
    print("offer type: " + params["type"])

    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    print("Created for %s", request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel):
        global io_channel
        io_channel = channel

        @channel.on("message")
        def on_message(message):
            if isinstance(message, str):
                if message.startswith("ch"):
                    new_channels = list(
                        map(lambda x: int(x), message.split(" ", 1)[1].split())
                    )
                    new_channels = {
                        "1": new_channels[0],
                        "2": new_channels[1],
                        "3": new_channels[2],
                        "4": new_channels[3],
                    }
                    global channels
                    channels = new_channels

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print("ICE connection state is %s", pc.iceConnectionState)
        if pc.iceConnectionState == "failed":
            await pc.close()
            pcs.discard(pc)
        elif pc.iceConnectionState == "closed":
            subprocess.Popen(
                "ps x | awk {'{print $1}'} | awk 'NR > 1' | xargs kill", shell=True
            )

    # handle offer
    await pc.setRemoteDescription(offer)
    for t in pc.getTransceivers():
        if t.kind == "video":
            pc.addTrack(VideoTrack())
            print("added track")

    # send answer
    answer = await pc.createAnswer()
    print("answer: " + str(answer))
    await pc.setLocalDescription(answer)
    print("sdp" + pc.localDescription.sdp)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def start_drone_connection(app):
    app["drone_connection"] = app.loop.create_task(connectToDrone(app))
    app["vehicle_status"] = app.loop.create_task(send_vehicle_status(app))


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


async def html(request):
    content = open(os.path.join("/home/pyrtc_ros", "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def client(request):
    content = open(os.path.join("/home/pyrtc_ros", "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def nipple(request):
    content = open(os.path.join("/home/pyrtc_ros", "nipple.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def index(request):
    content = open(os.path.join("/home/pyrtc_ros", "index.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def collection(request):
    content = open(os.path.join("/home/pyrtc_ros", "collection.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def manager(request):
    content = open(os.path.join("/home/pyrtc_ros", "manager.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def superjs(request):
    content = open(os.path.join("/home/pyrtc_ros", "super.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def utils(request):
    content = open(os.path.join("/home/pyrtc_ros", "utils.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def gauge(request):
    content = open(os.path.join("/home/pyrtc_ros", "gauge.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image topic to Webrtc stream")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8081)"
    )
    args = parser.parse_args()

    rospy.init_node("pyrtc_ros", anonymous=True, log_level=rospy.DEBUG)
    ImageConverter()

    app = web.Application()
    app.on_startup.append(start_drone_connection)
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", html)
    app.router.add_get("/client.js", client)
    app.router.add_post("/offer", offer)

    app.router.add_get("/nipple.js", nipple)
    app.router.add_get("/collection.js", collection)
    app.router.add_get("/index.js", index)
    app.router.add_get("/manager.js", manager)
    app.router.add_get("/super.js", superjs)
    app.router.add_get("/utils.js", utils)

    app.router.add_get("/gauge.js", gauge)

    # cors = aiohttp_cors.setup(
    #     app,
    #     defaults={
    #         "https://*.andremyers.dev": aiohttp_cors.ResourceOptions(
    #             allow_credentials=True, expose_headers="*", allow_headers="*"
    #         ),
    #         "https://{}.serveo.net".format(subdomain): aiohttp_cors.ResourceOptions(
    #             allow_credentials=True, expose_headers="*", allow_headers="*"
    #         ),
    #         "http://localhost:8080": aiohttp_cors.ResourceOptions(
    #             allow_credentials=True, expose_headers="*", allow_headers="*"
    #         ),
    #         "http://localhost:8081": aiohttp_cors.ResourceOptions(
    #             allow_credentials=True, expose_headers="*", allow_headers="*"
    #         ),
    #     },
    # )

    # for route in list(app.router.routes()):
    #     cors.add(route)

    web.run_app(app, access_log=None, port=args.port, ssl_context=None)
