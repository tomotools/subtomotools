#!/bin/bash

ref='ref/protein/cluster_targets.temb'

for FILE in tomo/embed/*.temb
do
	echo "Mapping $FILE"

	#export CUDA_VISIBLE_DEVICES=0,1
	tomotwin_map.py distance -r $ref -v $FILE -o map
	tomotwin_locate.py findmax -m map/map.tmap -o locate/

	f=$(basename "$FILE")

	mv locate/located.tloc locate/${f%%.*}.tloc
done

rm -r map
