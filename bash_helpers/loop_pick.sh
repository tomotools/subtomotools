#!/bin/bash

minmetric=0.99
maxmetric=1
minsize=80
maxsize=600
target='cluster_4'

for FILE in tloc/*.tloc
do
	echo "Extracting positions from $FILE"

	tomotwin_pick.py -l $FILE --target $target --minmetric $minmetric --maxmetric $maxmetric --minsize $minsize --maxsize $maxsize --o coords-temp

	f=$(basename "$FILE")

	touch coords/${f%%.*}.coords
	
	for COORDS in coords-temp/*.coords
	do
		cat $COORDS >> coords/${f%%.*}.coords
	done

done

rm -r coords-temp
