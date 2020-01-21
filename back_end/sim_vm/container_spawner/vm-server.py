#!/usr/bin/python3
import asyncio
import subprocess
import argparse
from aiohttp import web

# execute a subprocess and iterate through its stdout
def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


# spawn a container and await its complete spin up on the event loop
async def spawn(resp, subdomain):
    for line in execute(
        [
            "docker",
            "run",
            "-e",
            "SUBDOMAIN={}".format(subdomain),
            "--name",
            subdomain,
            "-it",
            "andremyers/drones:latest",
        ]
    ):
        await resp.write(line)
        await resp.drain()
        await asyncio.sleep(0.01)
        if "BUILD SUMMARY" in line.decode("utf-8"):
            subprocess.Popen(
                [
                    "docker",
                    "exec",
                    "-it",
                    subdomain,
                    "/bin/bash",
                    "-c",
                    "ssh -oStrictHostKeyChecking=no -R $(echo $SUBDOMAIN):80:localhost:8081 andrem.net",
                ]
            )
            await resp.write_eof()
            break


# route handler to spawn container
async def spawn_container(request):
    subdomain = request.rel_url.query["sd"]
    resp = web.StreamResponse(
        status=200, reason="OK", headers={"Content-Type": "text/html"}
    )
    await resp.prepare(request)
    await asyncio.wait([spawn(resp, subdomain)])
    return resp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server that spawns containers")
    parser.add_argument("--path")
    parser.add_argument("--port")
    args = parser.parse_args()

    app = web.Application()
    app.router.add_get("/api/sim", spawn_container)
    web.run_app(app, port=args.port, path=args.path)
