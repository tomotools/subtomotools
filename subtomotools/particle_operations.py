import os
import subprocess
from pathlib import Path

import click
import mrcfile
import numpy as np
import pandas as pd
import starfile
from tqdm import tqdm


@click.command()
@click.option(
    "--ctf",
    is_flag=True,
    default=False,
    show_default=True,
    help="Perform CTF correction prior to projection.",
)
@click.option(
    "-z",
    "--z-thickness",
    default=None,
    show_default=True,
    help="If given, project only central number of pixels.",
)
@click.option("-r", "--radius", help="Radius of particle in pixels, for normalization.")
@click.argument("input_star", nargs=1)
def project_particles(ctf, z_thickness, radius, input_star):
    """Project subtomograms to 2D.

    Takes starfile from Warp etc as input.
    Performs projection of all subtomograms listed.
    Writes out starfile to be used for 2D cleaning.

    """
    input_star = Path(input_star)

    particles = starfile.read(input_star)

    # Check if starfile is Relion >3.1 format.
    if "particles" in particles:
        particles = particles["particles"]

    print(f"Found {len(particles.index)} Particles to project.")

    # Prime some values, so that they only have to be read once
    with mrcfile.open(particles.iloc[0]["rlnImageName"]) as mrc:
        dim = mrc.data.shape
        angpix = mrc.voxel_size.x

    # Preallocate array to store results
    projections = np.empty((len(particles.index), dim[1], dim[2]), dtype=np.float32)

    with tqdm(total=len(particles.index)) as pbar:
        for index, row in particles.iterrows():
            subtomo = mrcfile.read(row["rlnImageName"])

            # Apply CTF as convolution with volume
            if ctf:
                subtomo_in = subtomo.copy()
                ctf_volume = mrcfile.read(row["rlnCtfImage"])

                # Check how the CTF volume is stored
                # Warp stores it in a FFTW-like way, which allows use of rfftn
                # rfftn returns the zero-frequency as the first item

                if not ctf_volume.shape == dim:
                    subtomo = np.fft.irfftn(
                        np.fft.rfftn(subtomo_in) * ctf_volume, s=subtomo_in.shape
                    )

                # Legacy approaches might store full array, use fftn
                else:
                    subtomo = np.real(np.fft.ifftn(np.fft.fftn(subtomo) * ctf_volume))

            # Use np.mean instead of np.sum to prevent overflow issues
            if z_thickness is not None:
                z_thickness = int(z_thickness)
                z_upper = int(np.floor(dim[0] / 2 + z_thickness / 2))
                z_lower = int(np.floor(dim[0] / 2 - z_thickness / 2))

                projections[index] = np.mean(subtomo[z_lower:z_upper], axis=0)

            else:
                # mrcfile reads as ZYX
                projections[index] = np.mean(subtomo.data, axis=0)

            pbar.update(1)

    print("Particles projected, writing out stack. \n")

    mrcs = mrcfile.new("temp.mrcs", overwrite=True)
    mrcs.set_data(projections)
    mrcs.set_image_stack()
    mrcs.voxel_size = angpix
    mrcs.close()

    # make particles star
    # Micrograph Name and XYZ are assumed to always be present
    particles_2d = pd.DataFrame()
    particles_2d["rlnMicrographName"] = particles["rlnMicrographName"]
    particles_2d["rlnCoordinateX"] = particles["rlnCoordinateX"]
    particles_2d["rlnCoordinateY"] = particles["rlnCoordinateY"]
    particles_2d["rlnCoordinateZ"] = particles["rlnCoordinateZ"]

    # Angles are only sometimes there, eg. after template matching
    # Assume that they all come together
    if "rlnAngleRot" in particles:
        particles_2d["rlnAngleRot"] = particles["rlnAngleRot"]
        particles_2d["rlnAngleTilt"] = particles["rlnAngleTilt"]
        particles_2d["rlnAnglePsi"] = particles["rlnAnglePsi"]

    # Translations are only sometimes there
    # Assume that they all come together
    if "rlnOriginXAngst" in particles:
        particles_2d["rlnOriginXAngst"] = particles["rlnOriginXAngst"]
        particles_2d["rlnOriginYAngst"] = particles["rlnOriginYAngst"]
        particles_2d["rlnOriginZAngst"] = particles["rlnOriginZAngst"]

    # New Info
    particles_2d["rlnImageName"] = [
        f"{i}@{input_star.with_name(input_star.stem)}_projected.mrcs"
        for i in range(1, len(particles.index) + 1)
    ]
    particles_2d["rlnOpticsGroup"] = "1"

    # Make _optics group for compatibility > 3.0
    # Microscope values don't matter as the CTF is pre-applied
    star_optics = pd.DataFrame.from_dict(
        [
            {
                "rlnOpticsGroupName": "opticsGroup1",
                "rlnOpticsGroup": "1",
                "rlnMicrographPixelSize": angpix,
                "rlnImageSize": dim[2],
                "rlnVoltage": "300",
                "rlnSphericalAberration": "2.7",
                "rlnAmplitudeContrast": "0.1",
                "rlnImageDimensionality": "2",
            }
        ]
    )

    starfile.write(
        {"optics": star_optics, "particles": particles_2d},
        f"{input_star.with_name(input_star.stem)}_projected.star",
    )

    subprocess.run(
        [
            "relion_preprocess",
            "--operate_on",
            "temp.mrcs",
            "--norm",
            "--bg_radius",
            str(radius),
            "--operate_out",
            f"{input_star.with_name(input_star.stem)}_projected.mrcs",
        ]
    )

    os.unlink("temp.mrcs")


@click.command()
@click.argument("subset_star", nargs=1)
@click.argument("subtomo_stars", nargs=-1)
def apply_subset(subset_star, subtomo_stars):
    """Apply subset selection to 3D dataset.

    Give the star file from subset selection job in relion, the star file(s)
    in which subtomograms are listed.
    Will output one starfile for each subtomogram star,
    in the structure expected for Warp.
    Uses the filename of the projections stack to match.

    """
    subset = starfile.read(subset_star, always_dict=True)
    subset = subset["particles"]

    subset["origin_star"] = subset["rlnImageName"].str.split("@", expand=True)[1]

    for st_star in subtomo_stars:
        fullset_3d = starfile.read(st_star, always_dict=True)
        subset_2d = subset[
            subset["rlnImageName"].str.split("@", expand=True)[1]
            == f"{Path(st_star).stem}_projected.mrcs"
        ]

        selected_idx = subset_2d["rlnImageName"].str.split("@", expand=True)[0].tolist()

        # indices in mrcs are 1-based
        selected_idx = [int(idx) - 1 for idx in selected_idx]

        subset_3d = fullset_3d["particles"].iloc[selected_idx].copy()

        # merge offsets xy and psi angle from 2d classification
        subset_3d["rlnAnglePsi"] = list(subset_2d["rlnAnglePsi"])
        subset_3d["rlnOriginXAngst"] = list(subset_2d["rlnOriginXAngst"])
        subset_3d["rlnOriginYAngst"] = list(subset_2d["rlnOriginXAngst"])

        # if group is given, take over
        if "rlnClassNumber" in subset_2d:
            subset_3d["rlnClassNumber"] = list(subset_2d["rlnClassNumber"])

        starfile.write(
            {"optics": fullset_3d["optics"], "particles": subset_3d},
            Path(st_star).with_name(f"{Path(st_star).stem}_selected.star"),
        )

        print(f"Wrote out {len(subset_3d.index)} particles from {st_star}. \n")

    # TODO: hand over to star_downgrade?
