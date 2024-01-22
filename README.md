# subtomotools
Scripts to facilitate STA, interfacing Warp/M, Relion 3.1, TomoTwin and whatever else seems relevant. 

## Functions:

### Star-file:
```upgrade-star```: Upgrade Warp-style star to Relion 3.1.4.  
```downgrade-star```: Downgrade Relion-3-style star for Warp/M.  
```dedup-3d```: Remove duplicate particles from star-file in 3D.  

### Particles:
```project-particles```: Calculate 2D projections of subtomograms, with or without CTF correction. CTF correction requires CTF volume.  
```apply-selection```: Apply subset of particles from 2D classification to subtomogram star.

### TomoTwin:
```tomotwin2warp```: Takes a folder of .coords files from TomoTwin, turns into star file based on prefix for subtomo reconstruction in Warp.

## Installation:

1. (Optional) create a fresh mamba/conda environment with Python >= 3.8:
`mamba create -n subtomotools python=3.8 -c conda-forge`
2. Install `subtomotools` from pip via `pip install "git+https://github.com/tomotools/subtomotools.git"`
3. Call the indiviudal programs directly from the command line and use `--help` to see options, e.g. `dedup-3d --help`
