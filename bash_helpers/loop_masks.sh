#!/bin/bash

for FILE in *.mrc
do
	if [[ -f masks/${FILE%%.*}mask.mrc ]]; then

		echo "Found mask for $FILE"
		
	else	
		echo "Making mask for $FILE"
		
		mod2mask --boundary 10 $FILE ${FILE%%.*}.mod

		mv ${FILE%%.*}_mask.mrc masks

	fi
done

