from pathlib import Path

import numpy as np
import pandas as pd


def parse_coords(coordsfile: Path):
    """Parse .coords as DataFrame."""
    coords = pd.DataFrame()

    coords = pd.read_csv(coordsfile, sep=" ", header=None)

    return coords


def scale_coordinates(coords: pd.DataFrame, scaling_factor: float):
    """Scale coordinates by scaling factor."""
    return coords.multiply(scaling_factor)


def list_close(positions: np.array, exclusion_dist: int):
    """List indices in np.array closer than distance threshold (radius).

    First point in sphere is retained.

    Input:
        positions: np.array with 3D coordinates as columns
        exclusion_dist: int value, minimum distance between coordinates

    Output:
        exclude_list: Indices of the points closer than exclusion radius.

    """
    exclude_list = []

    for i in range(0, len(positions)):
        if i in exclude_list:
            continue

        else:
            exclude_idx = np.where(
                euclidean_dist_3D(positions, positions[i]) < exclusion_dist
            )[0]

            if len(exclude_idx) > 1:
                exclude_idx_cleaned = np.delete(
                    exclude_idx, np.argwhere(exclude_idx == i)
                )

                exclude_list.extend(exclude_idx_cleaned.tolist())

    return exclude_list


def dedup(positions: np.array, exclusion_dist: int):
    """Deduplicate np.array based on distance threshold (radius).

    If multiple coordinates are found within the exclusion radius, only the
    first one survives.

    Input:
        positions: np.array with 3D coordinates as columns
        exclusion_dist: int value, minimum distance between coordinates

    Output:
        positions_dedup: XYZ coordinates of the surviving points.

    """
    exclude_list = list_close(positions, exclusion_dist)

    positions_dedup = np.delete(positions, exclude_list, axis=0)

    print(f"{positions_dedup.shape[0]} coordinates left after deduplication.")

    return pd.DataFrame(positions_dedup)


def euclidean_dist_3D(array, point):
    """Return Euclidean distance of all points in np.array (assumed XYZ) to point."""
    return np.sqrt(
        np.square(array[:, 0] - point[0])
        + np.square(array[:, 1] - point[1])
        + np.square(array[:, 2] - point[2])
    )
