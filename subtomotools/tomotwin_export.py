from pathlib import Path

import click
import pandas as pd
import starfile

import subtomotools.utils as utils


@click.command()
@click.option("--split/--nosplit",
              is_flag=True,
              default=False,
              show_default=True,
              help="Split star files based on prefix of tomogram, before first _")
@click.option(
    "--radius",
    "-r",
    default=1,
    type=int,
    show_default=True,
    help="The radius within only 1 pick should be considered, in px",
)
@click.argument("coords_folder", type=click.Path(), nargs=1)
def coords2warp(split, radius, coords_folder):
    """Creates a Warp-style star file from a folder of coordinates.

    Optionally, split into star-files based on prefix (before first "_")

    Radius of protein in pixels can be specified for deduplication of picks.

    """
    coords_folder = Path(coords_folder)

    uid_dict = {}

    for coord in coords_folder.glob("*.coords"):

        if split:
            # Split Unique ID / Name
            uid, name = coord.stem.split("_", maxsplit=1)
            name = name.rsplit("_", maxsplit=1)[0]

        else:
            uid = "particles"
            name = coord.stem

        # Create one output star per uid
        if uid not in uid_dict:
            uid_dict[uid] = pd.DataFrame()

        # improve naming for AreTomo-aligned TS
        if name.endswith("_ali_Imod"):
            name = name[:-5]

        # Parse coordinates for all references
        coords = utils.parse_coords(coord)

        print(f"{name}: found {len(coords.index)} coordinates.")

        # Remove particles closer than radius
        coords_dedup = utils.dedup(coords.values, radius)

        # Format as star columns
        coords_dedup.rename(
            columns={0: "rlnCoordinateX", 1: "rlnCoordinateY", 2: "rlnCoordinateZ"},
            inplace=True,
        )
        coords_dedup["rlnMicrographName"] = f"{name}.tomostar"

        # Append to full set
        uid_dict[uid] = pd.concat([coords_dedup, uid_dict[uid]])

    for uid in uid_dict:
        starfile.write(uid_dict[uid], coords_folder.parent / f"{uid}.star")

    return
