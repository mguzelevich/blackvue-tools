#!/usr/bin/bash

ffmpeg -i YDXJ0054.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0054.ts
ffmpeg -i YDXJ0083.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0083.ts
ffmpeg -i YDXJ0084.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0084.ts
ffmpeg -i YDXJ0089.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0089.ts
ffmpeg -i YDXJ0092.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0092.ts
ffmpeg -i YDXJ0093.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0093.ts
ffmpeg -i YDXJ0094.mp4 -acodec copy -vcodec copy -vbsf h264_mp4toannexb -f mpegts YDXJ0094.ts

ffmpeg -i "concat:YDXJ0054.ts|YDXJ0083.ts|YDXJ0084.ts|YDXJ0089.ts|YDXJ0092.ts|YDXJ0093.ts|YDXJ0094.ts" -acodec copy -vcodec copy out.mp4

# cut
# ffmpeg -ss 00:00:30 -i orginalfile -t 00:00:05 -vcodec copy -acodec copy newfile