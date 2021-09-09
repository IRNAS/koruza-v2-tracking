// follow https://github.com/nodesource/distributions/blob/master/README.md for tutorial on installation instructions

// getting started https://nodejs.org/en/docs/guides/getting-started-guide/
// run simply with node test_alignment_engine.js

console.log("Starting NodeJS alignment engine test script");

const IP = "192.168.76.118";
const ALIGNMENT_ENGINE_PORT = 8002;

// install xmlrpc with `npm install xmlrpc`
var xmlrpc = require("xmlrpc");
var fs = require("fs");

class TestXMLRPC {
    constructor() {
        // Creates an XML-RPC client. Passes the host information on where to
        // make the XML-RPC calls.
        this.alignment_engine_proxy = xmlrpc.createClient({ host: IP, port: ALIGNMENT_ENGINE_PORT, path: "/RPC2"})
        this.primary = null;
        this.secondary = null;

        this.alignment_engine_proxy.methodCall("initialize", [], (error, obj) => {
            // console.log("value: " + value);
            // return value is an array of string
            [this.primary, this.secondary] = obj;
            console.log("primary handle: " + this.primary);
            console.log("stringified :" + JSON.stringify(obj));
        });

        // this.alignment_engine_proxy.methodCall("get_picture", [], (error, value) => {
        //     console.log("value: " + value);
        //     console.log("primary handle: " + this.primary);
        // });
    }
}

alignment_engine_proxy = xmlrpc.createClient({ host: IP, port: ALIGNMENT_ENGINE_PORT, path: "/RPC2"})
function initialize() {
    return new Promise((resolve, reject) => {
        return alignment_engine_proxy.methodCall("initialize", [], (error, data) => {
            if (error) { return reject(error); }
            return resolve(data);
        });
    });
}
var ret = initialize();
var primary, secondary;
// console.log("primary: " + obj);
console.log("init return: " + ret.then((obj) => {
        console.log(obj);
        [primary, secondary] = obj;
    }));

function get_image(unit) {
    return new Promise((resolve, reject) => {
        return alignment_engine_proxy.methodCall("get_picture", [unit], (error, data) => {
            if (error) { return reject(error); }
            return resolve(data);
        });
    });
}

var ret = get_image(primary);
var img_data;
ret.then((obj) => {
    console.log(obj);
    img_data = obj;
    fs.writeFile('test.jpg', img_data, 'binary', function(err){
        if (err) throw err
        console.log('File saved.')
    })
})