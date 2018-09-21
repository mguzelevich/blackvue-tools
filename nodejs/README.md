# blackvue

This is a module to interact with BlackVue dashcams over their local Wi-Fi interface. It cannot use the BlackVue Cloud
to connect to a camera over the Internet. Consequently, the machine using this module needs to be connected to the Wi-Fi
signal broadcast by the camera, or otherwise able to connect to it.

This requires Node.js v8 or later. All applicable methods are `async`.

### Constructor
- `opts` - An object containing zero or more of the following properties
    - `ip` - The IP address of the camera. You probably don't need to set this. Defaults to `10.99.77.1`.
    - `port` The HTTP port. You almost definitely don't need to set this. Defaults to `80`.

Constructs a new instance of the BlackVue client. Example:

```js
const BlackVue = require('blackvue');
let bv = new BlackVue();
```

### getDownloadableFiles()

Returns a Promise which is resolved by an object with these properties:
- `mp4` - An array of video files
- `gps` - An array of GPS data files
- `3gf` - An array of accelerometer data files

Each element in each array is a string containing the path relative to the camera's root where the file can be
downloaded.

### getFileMetadata(path)
- `path` - The string path to the file (from `getDownloadableFiles`)

Returns a Promise which is resolved by an object with these properties:
- `size` - The file size in bytes
- `length` - The approximate length of time covered by this file, in seconds. This is measured by taking the difference of the timestamp in the filename and the `Last-Modified` header, so it's usually off by a second or two.

### downloadFileStream(path)
- `path` - The string path to the file (from `getDownloadableFiles`)

Returns a Promise which is resolved by an object with these properties:
- `metadata` - The metadata for the file, in the same format as `getFileMetadata`
- `stream` - The stream of the file

The stream may hang if the camera reboots or disconnects in the middle of the transfer. You're responsible for handling
this event on your own if you use this method.

If the file exists on the camera but is empty, the promise will be rejected with error message "Empty file".

### downloadFileToDisk(remotePath, localPath[, progressListener])
- `remotePath` - The string path to the file (from `getDownloadableFiles`)
- `localPath` - The string path where the file should be written (the directory must exist)
- `progressListener` - An optional function which will be called periodically with progress updates. It takes a single object argument with these properties:
    - `metadata` - The metadata for the file, in the same format as `getFileMetadata`
    - `bytesDownloaded` - The number of bytes downloaded
    - `elapsed` - The elapsed time of the download, in seconds
    - `eta` - The estimated time to completion, in seconds
    - `speed` - The average download rate for this entire download, in bytes per second

Returns a Promise which is resolved with no data when the download is complete.

### startStream([options])
- `options` - An optional object with the following options:
    - `camera` - Optional. Which camera you want to view. Specify either `BlackVue.Camera.Front` or `BlackVue.Camera.Rear`
    - `fps` - Optional. You can cap the number of frames emitted per second using this option. This has no effect on
    network activity between the camera and your application, it merely causes the module to drop frames received such
    that we only emit approximately this many frames per second. This might be useful if you are re-broadcasting the
    video stream over a limited data connection. The camera only sends approximately 10 frames per second and setting
    this higher than the camera's framerate has no effect.

Returns a Promise which is resolved with a `VideoStream` instance. `VideoStream` is an EventEmitter that emits `frame`
events for each JPEG frame it receives, and `end` when the stream ends. You can call `end()` on the stream object to
stop the stream.

Example:

```js
const BlackVue = require('blackvue');

let bv = new BlackVue();
bv.startStream({"camera": BlackVue.Camera.Rear}).then((stream) => {
    stream.on('frame', (jpeg) => {
        console.log("Got frame of size " + jpeg.length + " bytes");
    });

    stream.on('end', () => {
        console.log("Camera feed ended");
    });

    setTimeout(() => {
        stream.end();
    }, 10000);
});
```

Some caveats:
- You cannot reliably have two active streams at the same time
    - If you start a front-camera stream and, without ending it, start a rear camera stream, the initial front-camera
    stream will switch to the rear camera, and vice versa
    - If you start two streams then end one, the other will stop receiving frames but will not emit `end`
- It seems like streams may stop receiving frames without emitting `end` if you start downloading a recorded video
from the camera.
- Video streams are 704x480 @ ~10 FPS and around 400 kB/s. Each frame is a separately-compressed JPEG image.
