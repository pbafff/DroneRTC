const { google } = require('googleapis');
const express = require('express');
const fs = require('fs');
const https = require('https');
const express_ws = require('express-ws');
const cors = require('cors');

const compute = google.compute('v1');
let connections = 0;
let socketSwitch = true;
let startMsgSwitch = false;
const startMsg = 'Starting up simulator server. Please wait a moment...';

const app = express();
const server = https.createServer({
    key: fs.readFileSync('/home/andre/ws_server/privkey.pem'),
    cert: fs.readFileSync('/home/andre/ws_server/cert.pem'),
}, app)
    .listen(4433, () => console.log('Listening on port 4433'));
const expressWs = express_ws(app, server);
const aWss = expressWs.getWss('/');


app.use(cors());

app.get('/switch', (req, res) => {
    socketSwitch = !socketSwitch;
    if (socketSwitch && !connections) droneSimVmSwitch(false);
    const status = `socket is now ${socketSwitch ? 'on' : 'off'}\n`;
    console.log(status);
    res.send(status);
    res.status(200).end();
});

app.ws('/', (ws, req) => {
    if (startMsgSwitch) ws.send(startMsg);
    console.log('new client', req.ip);
    adjustClientCount(true);
    ws.on('close', () => {
        if (socketSwitch) {
            console.log('client disconnect', req.ip);
            if (connections > 0) adjustClientCount(false);
        }
        else {
            connections--;
        }
    });
});

function adjustClientCount(direction) {
    const initial = connections;
    if (direction) connections++;
    else connections--;
    droneSimVmSwitch(initial);
}

function droneSimVmSwitch(initial) {
    if (!connections) {
        //shut down vm
        console.log('shutting down sim');
        authorize(function (authClient) {
            const request = {
                project: 'exalted-entity-227608',
                zone: 'us-east1-c',
                instance: 'drone-sim-vm',
                auth: authClient,
            };
            compute.instances.get(request, function (err, res) {
                const status = res.data.status;
                if (err) {
                    console.error(err);
                    return;
                }
                if (status == "RUNNING") {
                    compute.instances.stop(request, function (err, res) {
                        if (err) {
                            console.error(err);
                            return;
                        }
                    });
                }
            });
        });
    }
    else if (!initial && connections === 1) {
        //check if sim is on if not turn on sim
        console.log('turning on vm');
        authorize(function (authClient) {
            const request = {
                project: 'exalted-entity-227608',
                zone: 'us-east1-c',
                instance: 'drone-sim-vm',
                auth: authClient,
            };
            compute.instances.get(request, async function (err, res) {
                const status = res.data.status;
                if (err) {
                    console.error(err);
                    return;
                }
                console.log(status);
                if (status == "RUNNING") return;
                else if (status == "TERMINATED" || status == "STOPPING" || status == "SUSPENDING") {
                    aWss.clients.forEach(function (client) {
                        client.send(startMsg);
                    });
                    console.log('polling');
                    const startRes = await pollStart(request);
                    aWss.clients.forEach(function (client) {
                        client.send(startRes);
                    });
                }
            });
        });
    }
}

function authorize(callback) {
    google.auth.getApplicationDefault(function (err, authClient) {
        if (err) {
            console.error('authentication failed: ', err);
            return;
        }
        if (authClient.createScopedRequired && authClient.createScopedRequired()) {
            const scopes = ['https://www.googleapis.com/auth/cloud-platform'];
            authClient = authClient.createScoped(scopes);
        }
        callback(authClient);
    });
}

async function pollStart(request) {
    startMsgSwitch = true;
    let exit = false;
    let value;
    while (!exit) {
        await new Promise(r => setTimeout(r, 2000));
        compute.instances.start(request, function (err, res) {
            if (err) {
                console.error(err);
                value = JSON.stringify(err);
            }
        });
        compute.instances.get(request, function (err, res) {
            const status = res.data.status;
            if (err) {
                console.error(err);
                value = JSON.stringify(err);
                return;
            }
            console.log(status);
            if (status == "RUNNING") {
                exit = true;
                startMsgSwitch = false;
                value = 'Server online! Launching simulator.';
            }
        });
    }
    return value;
}
