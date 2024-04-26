#!/bin/bash

for FILE in *.mrc
do
	if [[ -f embed/${FILE%%.*}_embeddings.temb ]]; then

		echo "Found embedding for $FILE"
		
	else	
		echo "Embedding $FILE"

		export CUDA_VISIBLE_DEVICES=0,1
		# batch size: 3080 180 / GPU, 2080 210 / GPU		
		tomotwin_embed.py tomogram -m ~/tomotwin_model_p120_052022_loss.pth -v $FILE -o embed -s 2 --mask masks/${FILE%%.*}_mask.mrc -b 420

	fi
done

