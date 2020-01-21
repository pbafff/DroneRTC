import nipplejs from './index.js'

let ch1 = 1500;
let ch2 = 1500;
let ch3 = 1500;
let ch4 = 1500;
let channels = `ch ${ch1} ${ch2} ${ch3} ${ch4}`;
let thrust = 0;
let roll = 0;

//============================JOYSTICKS==============================

const joystickRight = nipplejs.create({
    zone: document.querySelector('#right-stick-zone'),
    mode: 'static',
    position: { top: '50%', right: '50%' },
    color: 'red'
});

joystickRight.on('move', function (e, data) {
    const stickPos = findNewPoint(0, 0, data.angle.degree, data.distance);
    ch2 = convertToPWM(-stickPos.y); //pitch
    ch4 = convertToPWM(stickPos.x); //yaw
});

const joystickLeft = nipplejs.create({
    zone: document.querySelector('#left-stick-zone'),
    mode: 'static',
    position: { top: '50%', right: '50%' },
    color: 'grey'
});

joystickLeft.on('move', function (e, data) {
    const stickPos = findNewPoint(0, 0, data.angle.degree, data.distance);
    ch1 = convertToPWM(stickPos.x); //roll
    ch3 = convertToPWM(stickPos.y); //thrust
});

const frontLeft = document.querySelector('#left-stick-zone > .nipple > .front');
frontLeft.addEventListener('click', leftRelease, false);
frontLeft.addEventListener('touchend', leftRelease, false);
function leftRelease() {
    ch1 = 1500;
    ch3 = 1500;
}

const frontRight = document.querySelector('#right-stick-zone > .nipple > .front');
frontRight.addEventListener('click', rightRelease, false);
frontRight.addEventListener('touchend', rightRelease, false);
function rightRelease() {
    ch2 = 1500;
    ch4 = 1500;
}

function findNewPoint(x, y, angle, distance) {
    const result = {};
    result.x = Math.round(Math.cos(angle * Math.PI / 180) * distance + x);
    result.y = Math.round(Math.sin(angle * Math.PI / 180) * distance + y);
    return result;
}

function convertToPWM(val) {
    const rounded = val.toFixed(4);
    const slope = (2000 - 1000) / (50 - -50);
    return 1000 + slope * (rounded - -50);
}

//====================WASD CONTROLS================================

document.addEventListener('keydown', function (e) {
    switch (e.keyCode) {
        case 87: //w
            thrust = 1;
            break;
        case 65: //a
            roll = -1;
            break;
        case 83: //s
            thrust = -1;
            break;
        case 68: //d
            roll = 1;
            break;
    }
});

document.addEventListener('keyup', function (e) {
    switch (e.keyCode) {
        case 87: //w 
            thrust = 0;
            break;
        case 65: //a
            roll = 0;
            break;
        case 83: //s
            thrust = 0;
            break;
        case 68: //d
            roll = 0;
            break;
    }
});

setInterval(() => {
    if (thrust == 1 && ch3 < 2000) ch3 += 10;
    else if (thrust === -1 && ch3 > 1000) ch3 -= 10;
    thrustGauge.setValueAnimated(ch3, 0.5);
}, 20);

setInterval(() => {
    if (roll == 1 && ch1 < 2000) ch1 += 10;
    else if (roll === -1 && ch1 > 1000) ch1 -= 10;
    rollGauge.setValueAnimated(ch1, 0.5);
}, 20);

const thrustGauge = Gauge(
    document.getElementById("thrust-gauge"), {
        min: 1000,
        max: 2000,
        dialStartAngle: 180,
        dialEndAngle: 0,
        value: 1500,
        color: function (value) {
            if (value < -25) {
                return "#5ee432";
            } else if (value < 0) {
                return "#fffa50";
            } else if (value < 25) {
                return "#f7aa38";
            } else {
                return "#ef4655";
            }
        }
    }
);

const rollGauge = Gauge(
    document.getElementById("roll-gauge"), {
        min: 1000,
        max: 2000,
        dialStartAngle: 180,
        dialEndAngle: 0,
        value: 1500,
        color: function (value) {
            if (value < -25) {
                return "#5ee432";
            } else if (value < 0) {
                return "#fffa50";
            } else if (value < 25) {
                return "#f7aa38";
            } else {
                return "#ef4655";
            }
        }
    }
);

//============================PEER CONNECTION==============================

let dc;
let pc;

const info = document.getElementById('info');
window.onload = function () {
    info.value = "";
    start();

    setInterval(() => {
        if (dc.readyState == 'open') {
            channels = `ch ${ch1} ${ch2} ${ch3} ${ch4}`;
            dc.send(channels);
        }
    }, 40);
}

function start() {
    pc = createPeerConnection();
    dc = pc.createDataChannel('io', { "ordered": false, "maxRetransmits": 0 });

    dc.onclose = function () {
        console.log('data channel closed');
    };
    dc.onopen = function () {
        dc.send(`start time: ${new Date().getTime()}`);
    };
    dc.onmessage = function (e) {
        if (e.data.startsWith('init ')) {
            document.getElementById('info').value += `${e.data.slice(5)}\n`;
            info.scrollTop = info.scrollHeight;
        }
        else {
            document.getElementById('info').value = e.data;
        }
    };
    negotiate();
}

function createPeerConnection() {
    const config = {
        iceServers: [{ urls: ['stun:stun.l.google.com:19302'] }]
    };

    const newPc = new RTCPeerConnection(config);

    //listeners for debugging
    newPc.addEventListener('icegatheringstatechange', function () {
        console.debug(newPc.iceGatheringState);
    }, false);

    newPc.addEventListener('iceconnectionstatechange', function () {
        console.debug(newPc.iceConnectionState);
    }, false);

    newPc.addEventListener('signalingstatechange', function () {
        console.debug(newPc.signalingState);
    }, false);

    //connect video
    newPc.addEventListener('track', function (e) {
        if (e.track.kind == 'video')
            document.getElementById('video').srcObject = e.streams[0];
    });

    return newPc;
}

function negotiate() {
    return pc.createOffer({
        offerToReceiveVideo: true
    }).then(function (offer) {
        return pc.setLocalDescription(new RTCSessionDescription(offer));
    }).then(function () {
        //wait for all ICE candidates
        return new Promise(function (resolve) {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                function checkState() {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                }
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(function () {
        const offer = pc.localDescription;
        console.log({
            sdp: offer.sdp,
            type: offer.type,
        });
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function (res) {
        return res.json();
    }).then(function (answer) {
        console.debug(answer);
        return pc.setRemoteDescription(answer);
    }).catch(function (e) {
        alert(e);
    });
}
