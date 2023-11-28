import collections
from pathlib import Path

import click
import mrcfile
import pandas as pd
import starfile

from subtomotools import utils


@click.command()
@click.option(
    "--amp",
    default=0.07,
    show_default=True,
    help="Amplitude contrast given during CTF estimation.",
)
@click.argument("star", nargs=1)
def upgrade_star(amp, star):
    """Take subtomogram starfile from Warp and make it compatible with Relion 3.1.4."""
    star = Path(star)

    particles = starfile.read(star)

    # Check values for optics header
    angpix = None

    if "rlnPixelSize" in particles:
        angpix = particles["rlnPixelSize"][0]
        del particles["rlnPixelSize"]

    if "rlnVoltage" in particles:
        voltage = particles["rlnVoltage"][0]
        del particles["rlnVoltage"]
    else:
        voltage = 300

    if "rlnSphericalAberration" in particles:
        cs = particles["rlnSphericalAberration"][0]
        del particles["rlnSphericalAberration"]
    else:
        cs = 2.7

    with mrcfile.open(particles.iloc[0]["rlnImageName"]) as mrc:
        dim = mrc.data.shape
        if angpix is None:
            angpix = mrc.voxel_size.x

    del particles["rlnMagnification"]
    del particles["rlnDetectorPixelSize"]

    particles["rlnOpticsGroup"] = "1"

    # If rlnOrigin is given, convert to Angstrom
    if "rlnOriginX" in particles:
        particles["rlnOriginXAngst"] = particles["rlnOriginX"].multiply(angpix)
        particles["rlnOriginYAngst"] = particles["rlnOriginY"].multiply(angpix)
        del particles["rlnOriginX"]
        del particles["rlnOriginY"]

    # Treat Z separately in case of 2D data
    if "rlnOriginZ" in particles:
        particles["rlnOriginZAngst"] = particles["rlnOriginZ"].multiply(angpix)
        del particles["rlnOriginZ"]

    # Make _optics group for compatibility > 3.0
    star_optics = pd.DataFrame.from_dict(
        [
            {
                "rlnOpticsGroupName": star.stem,
                "rlnOpticsGroup": "1",
                "rlnMicrographPixelSize": angpix,
                "rlnImageSize": dim[2],
                "rlnVoltage": voltage,
                "rlnSphericalAberration": cs,
                "rlnAmplitudeContrast": amp,
                "rlnImageDimensionality": "3",
            }
        ]
    )

    starfile.write(
        {"optics": star_optics, "particles": particles},
        f"{star.with_name(star.stem)}_upgraded.star",
    )


@click.command()
@click.option(
    "--m",
    is_flag=True,
    default=False,
    show_default=True,
    help="Make .star minimal for use with Warp/M.",
)
@click.argument("star", nargs=1)
def downgrade_star(m, star):
    """Take subtomogram starfile from Relion 3.1.4 and make it compatible to Warp."""
    star = Path(star)

    star_parsed = starfile.read(star)

    particles = star_parsed["particles"]

    # Remove entries related to optics groups
    del particles["rlnOpticsGroup"]
    del particles["rlnGroupNumber"]

    # Add some optics info instead
    angpix = star_parsed["optics"].iloc[0]["rlnMicrographPixelSize"]

    particles["rlnMagnification"] = 10000
    particles["rlnDetectorPixelSize"] = angpix

    # If rlnOrigin is given, convert to pixels
    if "rlnOriginXAngst" in particles:
        particles["rlnOriginX"] = particles["rlnOriginXAngst"].divide(angpix)
        particles["rlnOriginY"] = particles["rlnOriginYAngst"].divide(angpix)
        del particles["rlnOriginXAngst"]
        del particles["rlnOriginYAngst"]

    # Treat Z separately in case of 2D data
    if "rlnOriginZAngst" in particles:
        particles["rlnOriginZ"] = particles["rlnOriginZAngst"].divide(angpix)
        del particles["rlnOriginZAngst"]

    if m:
        particles_m = pd.DataFrame()
        particles_m["rlnCoordinateX"] = particles["rlnCoordinateX"]
        particles_m["rlnCoordinateY"] = particles["rlnCoordinateY"]
        particles_m["rlnCoordinateZ"] = particles["rlnCoordinateZ"]

        def mrc2tomostar(str):
            return str.replace(".mrc", ".tomostar")

        particles_m["rlnMicrographName"] = particles["rlnMicrographName"].apply(
            mrc2tomostar
        )

        particles_m["rlnAngleRot"] = particles["rlnAngleRot"]
        particles_m["rlnAngleTilt"] = particles["rlnAngleTilt"]
        particles_m["rlnAnglePsi"] = particles["rlnAnglePsi"]

        particles_m["rlnOriginX"] = particles["rlnOriginX"]
        particles_m["rlnOriginY"] = particles["rlnOriginY"]
        particles_m["rlnOriginZ"] = particles["rlnOriginZ"]

        particles_m["rlnImageName"] = particles["rlnImageName"]
        particles_m["rlnCtfImage"] = particles["rlnCtfImage"]

        starfile.write(particles_m, f"{star.with_name(star.stem)}_downgraded_data.star")

    else:
        starfile.write(particles, f"{star.with_name(star.stem)}_downgraded.star")


@click.command()
@click.option(
    "--radius",
    "-r",
    default=1,
    type=int,
    show_default=True,
    help="Deduplication radius in pixels.",
)
@click.argument("input_star", type=click.Path(), nargs=1)
def dedup_3d(radius, input_star):
    """Deduplicate particles in a star file in 3D.

    Input star-file (either with or without optics groups) and a radius.
    If present, takes shifts (rlnOriginXYZ) into account.

    Radius is in pixels, using the pixel spacing which is reflected in the

    """
    input_star = Path(input_star)

    star = starfile.read(input_star)

    # Make sure both older and newer star files are handled properly
    if type(star) is collections.OrderedDict:
        particles = star["particles"]
    else:
        particles = star

    # Create unique tomo ID based on Warp Session and Micrograph Name!
    def return_session(str):
        return str.split("/")[-4]

    particles["tomo_uid"] = (
        particles["rlnImageName"].apply(return_session)
        + "_"
        + particles["rlnMicrographName"]
    )

    particles_dedup = pd.DataFrame()

    # Iterate over unique tomograms
    for tomo in particles["tomo_uid"].unique():
        particles_selected = particles[particles["tomo_uid"] == tomo]
        particles_selected.reset_index(drop=True, inplace=True)

        # Calculate shifted XYZ
        df_temp = pd.DataFrame()

        if "rlnOriginXAngst" in particles_selected:
            angpix = star["optics"]["rlnMicrographPixelSize"][0]

            df_temp["X"] = particles_selected["rlnCoordinateX"] - (
                particles_selected["rlnOriginXAngst"].divide(angpix)
            )
            df_temp["Y"] = particles_selected["rlnCoordinateY"] - (
                particles_selected["rlnOriginYAngst"].divide(angpix)
            )
            df_temp["Z"] = particles_selected["rlnCoordinateZ"] - (
                particles_selected["rlnOriginZAngst"].divide(angpix)
            )
        elif "rlnOriginX" in particles_selected:
            df_temp["X"] = (
                particles_selected["rlnCoordinateX"] - particles_selected["rlnOriginX"]
            )
            df_temp["Y"] = (
                particles_selected["rlnCoordinateY"] - particles_selected["rlnOriginY"]
            )
            df_temp["Z"] = (
                particles_selected["rlnCoordinateZ"] - particles_selected["rlnOriginZ"]
            )
        else:
            df_temp["X"] = particles_selected["rlnCoordinateX"]
            df_temp["Y"] = particles_selected["rlnCoordinateY"]
            df_temp["Z"] = particles_selected["rlnCoordinateZ"]

        # Remove based on distance threshold
        too_close_idx = utils.list_close(df_temp.values, radius)

        particles_dedup_temp = particles_selected.drop(set(too_close_idx), axis=0)

        particles_dedup = pd.concat([particles_dedup, particles_dedup_temp])

    # Remove duplicate entries (if multiple classifications were merged)
    particles_dedup = particles_dedup.drop_duplicates(
        subset=["rlnImageName"], keep="first"
    )

    # Remove uuid column
    del particles_dedup["tomo_uid"]

    print(
        f"{len(particles_dedup.index)} of {len(particles.index)} particles retained."
    )

    if type(star) is collections.OrderedDict:
        starfile.write(
            {"optics": star["optics"], "particles": particles_dedup},
            input_star.with_stem(f"{input_star.stem}_dedup"),
        )
    else:
        starfile.write(
            particles_dedup, input_star.with_stem(f"{input_star.stem}_dedup")
        )

    return
