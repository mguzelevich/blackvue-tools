#!/usr/bin/bash

days=$(
	find ./gps -name "*_*.gps" -type f | sed 's|\./gps/\(.*\)_\(.*\)_\(.*\.gps\)|\1|' | sort -u
)

# IFS=";"
echo -e "$days" | while read d; do
	echo -e "${d} process"
	find ./gps -name "${d}_*.gps" -type f -exec cat {} \; | sort -u > ./${d}.gps
done
