const Events = require('events');
const Util = require('util');

Util.inherits(VideoStream, Events.EventEmitter);

module.exports = VideoStream;

/**
 * @param {ClientRequest} req
 * @param {Readable} rawStream
 * @param {string} boundary
 * @param {object} options
 * @constructor
 * @private
 */
function VideoStream(req, rawStream, boundary, options) {
	this._req = req;
	this._stream = rawStream;
	this._boundary = Buffer.from(boundary + "\r\n", 'ascii');
	this._options = options;
	this._setup();
}

/**
 * @private
 */
VideoStream.prototype._setup = function() {
	let buf = Buffer.alloc(0);
	let pos;

	this._lastFrameTime = 0;
	if (this._options.fps) {
		// the camera seems to send at 10 fps so let's deduct 100ms here so we get as close to our desired fps as possible
		this._msBetweenFrames = Math.round(1000 / this._options.fps) - 100;
	}

	this._stream.on('data', (chunk) => {
		buf = Buffer.concat([buf, chunk]);
		while ((pos = buf.indexOf(this._boundary)) != -1) {
			// we have a complete frame, and it ends at `pos`
			this._handleFrame(buf.slice(0, pos));
			buf = buf.slice(pos + this._boundary.length);
		}
	});

	this._stream.on('error', (err) => {
		// not critical enough to crash really
	});

	this._stream.on('end', () => {
		this.emit('end');
	});
};

/**
 * Strip the headers from a frame.
 * @param {Buffer} frame
 * @private
 */
VideoStream.prototype._handleFrame = function(frame) {
	if (this._msBetweenFrames && Date.now() - this._lastFrameTime < this._msBetweenFrames) {
		return; // drop the frame
	}

	this._lastFrameTime = Date.now();
	this.emit('frame', frame.slice(frame.indexOf("\r\n\r\n") + 4));
};

/**
 * Stop the stream.
 */
VideoStream.prototype.end = function() {
	this._req.abort();
};
