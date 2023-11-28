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
```tomotwin2warp```: **not included yet**, will be conversion of a tomotwin-generated coords directory to a Warp-style star