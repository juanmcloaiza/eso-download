"""
ESO archive downloader CLI.

This script provides a command-line interface to query and download
ESO raw and Phase3 archive data.

Requirements
------------

 - Python >= 3.10
 - astroquery >= 0.4.12 (currently pre-release)

    ```
    $ python -m pip install -U --pre astroquery --no-cache-dir
    ```

Recommendation
--------------

    To use the script as a command, make it executable and
    add it to some deirectory in your $PATH, e.g., /us/local/bin:

        $ chmod +x eso-download.py
        $ mv eso-download.py /usr/local/bin/

    Now you can run it from anywhere as in the examples below.

Usage examples
--------------

Raw archive::

    eso-download raw --help

    eso-download raw --user <user> \
        --run-id "090.C-0733(A)" \
        --instrument FORS2

    eso-download raw --user <user> \
        --ra 129.0629 --dec -26.4093 \
        --max-rows 20

    eso-download raw --run-id '090.C-0733(A)' \
        --instrument FORS2 \
        --start-date 2013-01-01 --end-date 2013-04-01 \
        --file-cat SCIENCE \
        --max-rows 30 --metadata-only

Phase3 archive::

    eso-download phase3 --help

    eso-download phase3 --user <user> \
        --proposal-id "094.B-0345(A)" \
        --collection MUSE

    eso-download phase3 --user <user> \
        --target-name "NGC 253"

    eso-download phase3 --proposal-id '275.A-5060(A)' \
        --instrument FORS2 \
        --target-name 'GDS J033223' \
        --ra 53.1 --dec -27.73\
        --publication-date-min 2014-07-11 --publication-date-max 2014-07-12 \
        --facility ESO-VLT-U1 \
        --max-rows 30 --metadata-only

General options::

    eso-download raw --count-only
    eso-download phase3 --metadata-only


Authenticate / Deauthenticate:

    eso-download [raw|phase3] --user <username>
    # Downloads data and metadata available to user <username>
    # Prompts password if not yet unauthenticated.

    eso-download [raw|phase3] --user <username> --deauthenticate
    # Deletes password from keyring;
    # Password for <username> will need to be re-entered next time.
"""

import os
import sys
import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union, Dict, Any, Iterable, List
from packaging.version import Version
import keyring
from astropy.table import Table
import astroquery
from astroquery.eso import Eso


ASTROQUERY_MIN_VER = "0.4.12.dev10525"
ASTROQUERY_INSTALL = "python -m pip install -U --pre astroquery --no-cache-dir"


def require_version(pkg, minimum, how_to_install_message):
    """Provides a useful message if the required version is not installed"""
    if Version(pkg.__version__) < Version(minimum):
        sys.exit(
            f"{pkg.__name__} >= {minimum} required, "
            f"found {pkg.__version__}\n"
            "Install the latest version:\n"
            f"{how_to_install_message}"
        )


# ------------ #
#  COMMON API
# ------------ #

DEFAULT_RADIUS_DEG: float = 10.0 / 60.0  # 10 arcmin


@dataclass
class Cone:
    """Simple container for sky cone search parameters."""

    ra: Optional[float] = None
    dec: Optional[float] = None
    radius: Optional[float] = None

    @classmethod
    def from_args(
        cls,
        args: argparse.Namespace,
        default_radius: float
    ) -> "Cone":
        """Create a Cone from parsed CLI arguments."""
        if args.ra is None or args.dec is None:
            return cls()
        return cls(float(args.ra), float(args.dec), default_radius)


class BaseEsoDownloader(ABC):
    """Base class for ESO archive downloaders."""

    def __init__(
        self,
        *,
        user: Optional[str] = None,
        deauthenticate: bool = False,
        max_rows: int = 100,
        outdir: str = ".",
        with_calib: Optional[str] = None,
        count_only: bool = False,
        metadata_only: bool = False,
    ) -> None:
        self.eso = Eso()
        self.eso.ROW_LIMIT = max_rows
        self.outdir = outdir
        self.with_calib = with_calib
        self.count_only = count_only
        self.metadata_only = metadata_only

        self.user = user
        self.deauthenticate = deauthenticate
        self.authenticated: bool = False
        self.authenticate()

    def authenticate(self):
        if self.user:
            if self.deauthenticate:
                try:
                    keyring.delete_password('astroquery:www.eso.org', self.user)
                except keyring.errors.PasswordDeleteError as e:
                    print(e)
            else:
                self.eso.login(username=self.user, store_password=True)
                if not self.eso.authenticated():
                    keyring.delete_password('astroquery:www.eso.org', self.user)
                    raise RuntimeError("Authentication failed")
                self.authenticated = True

    @abstractmethod
    def retrieve_metadata(self) -> Union[Table, int, str]:
        """Queries ESO archive metadata."""

    def write_table_as_csv(self, table: Any) -> Optional[str]:
        """Write an Astropy table to CSV in the output directory."""
        if table is None:
            return None

        os.makedirs(self.outdir, exist_ok=True)
        path = os.path.join(self.outdir, "query_results.csv")
        table.write(path, overwrite=True)
        return path

    def retrieve_data(self, dp_ids: Iterable[str]) -> Union[str, List[str]]:
        """Download datasets by DP IDs."""
        return self.eso.retrieve_data(
            dp_ids,
            destination=self.outdir,
            with_calib=self.with_calib,
            unzip=True,
        )


def record_count(t: Any) -> int:
    """Return the number of records in a query result."""
    try:
        rc = len(t)
    except TypeError:
        rc = 0 if t is None else int(t)
    return rc


def run_pipeline(downloader: BaseEsoDownloader) -> Optional[Union[str, List[str]]]:
    """Execute pipeline: query -> save metadata -> download data"""
    print("Querying ESO archive...")
    table = downloader.retrieve_metadata()

    print(f"Found {record_count(table)} datasets...")
    if downloader.count_only:
        return None

    path = downloader.write_table_as_csv(table)
    print(f"Records written to {path}")

    if downloader.metadata_only:
        return None

    dp_ids = list(table["dp_id"])
    files = downloader.retrieve_data(dp_ids)
    return files

# ------------#
# Phase3 API
# ------------#


class Phase3Downloader(BaseEsoDownloader):
    """Downloader for ESO Phase3 (processed) archive."""

    def __init__(
        self,
        *,
        collection: Optional[str] = None,
        cone: Optional[Cone] = None,
        filters: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.collection = collection
        self.cone = cone or Cone()
        self.filters = filters or {}

    def retrieve_metadata(self) -> Union[Table, int, str]:
        """Query Phase3 archive metadata."""
        return self.eso.query_surveys(
            surveys=self.collection,
            cone_ra=self.cone.ra,
            cone_dec=self.cone.dec,
            cone_radius=self.cone.radius,
            column_filters=self.filters,
            count_only=self.count_only,
            authenticated=self.authenticated,
        )


def build_filters_phase3(parsed_args: argparse.Namespace) -> Dict[str, str]:
    """Build Phase3 query filter dictionary."""
    filters: Dict[str, str] = {}

    if parsed_args.proposal_id:
        filters["proposal_id"] = f"='{parsed_args.proposal_id}'"

    if parsed_args.target_name:
        filters["target_name"] = f"like '%{parsed_args.target_name}%'"

    if parsed_args.instrument:
        filters["instrument_name"] = f"='{parsed_args.instrument}'"

    if parsed_args.facility:
        filters["facility_name"] = f"='{parsed_args.facility}'"

    # Release date
    if parsed_args.release_date_min and parsed_args.release_date_max:
        filters["obs_release_date"] = (
            f"between '{parsed_args.release_date_min}' "
            f"and '{parsed_args.release_date_max}'"
        )
    elif parsed_args.release_date_min:
        filters["obs_release_date"] = f">='{parsed_args.release_date_min}'"
    elif parsed_args.release_date_max:
        filters["obs_release_date"] = f"<='{parsed_args.release_date_max}'"

    # Publication date
    if parsed_args.publication_date_min and parsed_args.publication_date_max:
        filters["publication_date"] = (
            f"between '{parsed_args.publication_date_min}' "
            f"and '{parsed_args.publication_date_max}'"
        )
    elif parsed_args.publication_date_min:
        filters["publication_date"] = f">='{parsed_args.publication_date_min}'"
    elif parsed_args.publication_date_max:
        filters["publication_date"] = f"<='{parsed_args.publication_date_max}'"

    return filters


# ---------#
# Raw API
# ---------#


class RawDownloader(BaseEsoDownloader):
    """Downloader for ESO raw archive."""

    def __init__(
        self,
        *,
        instrument: Optional[str] = None,
        cone: Optional[Cone] = None,
        filters: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.instrument = instrument
        self.cone = cone or Cone()
        self.filters = filters or {}

    def retrieve_metadata(self) -> Union[Table, int, str]:
        """Query raw archive metadata."""
        return self.eso.query_main(
            instruments=self.instrument,
            cone_ra=self.cone.ra,
            cone_dec=self.cone.dec,
            cone_radius=self.cone.radius,
            column_filters=self.filters,
            count_only=self.count_only,
            authenticated=self.authenticated,
        )


def build_filters_raw(parsed_args: argparse.Namespace) -> Dict[str, str]:
    """Build raw archive query filter dictionary."""
    filters: Dict[str, str] = {}

    if parsed_args.run_id:
        filters["prog_id"] = f"='{parsed_args.run_id}'"

    if parsed_args.file_cat:
        filters["dp_cat"] = f"='{parsed_args.file_cat}'"

    if parsed_args.target_name:
        filters["target"] = f"like '%{parsed_args.target_name}%'"

    if parsed_args.start_date and parsed_args.end_date:
        filters["exp_start"] = (
            f"between '{parsed_args.start_date}' and '{parsed_args.end_date}'"
        )
    elif parsed_args.start_date:
        filters["date_obs"] = f">='{parsed_args.start_date}'"
    elif parsed_args.end_date:
        filters["date_obs"] = f"<='{parsed_args.end_date}'"

    return filters

# -------------#
# Phase 3 CLI
# -------------#


def register_phase3_subparser(
    subparsers: argparse._SubParsersAction,
    add_shared_args
) -> None:
    """Register Phase3 CLI subcommand."""
    p = subparsers.add_parser("phase3", help="Download ESO archive phase3 data")
    add_shared_args(p)

    p.add_argument("--target-name", help="Target name (metadata match)")
    p.add_argument("--ra", type=float, help="Right Ascension in degrees")
    p.add_argument("--dec", type=float, help="Declination in degrees")
    p.add_argument("--proposal-id",
                   help="ESO Proposal ID (e.g. 094.B-0345(A))")
    p.add_argument("--instrument", help="Instrument name (e.g. MUSE)")
    p.add_argument(
        "--collection", help="Observation collection name (e.g. MUSE)")
    p.add_argument("--facility", help="Facility name (e.g. ESO-VLT-U4)")

    p.add_argument("--release-date-min",
                   help="Release date range start (YYYY-MM-DD)")
    p.add_argument("--release-date-max",
                   help="Release date range end (YYYY-MM-DD)")
    p.add_argument("--publication-date-min",
                   help="Publication date range start (YYYY-MM-DD)")
    p.add_argument("--publication-date-max",
                   help="Publication date range end (YYYY-MM-DD)")

    p.set_defaults(func=handle_phase3)


def handle_phase3(p_args: argparse.Namespace) -> None:
    """Handle Phase3 CLI command."""
    downloader = Phase3Downloader(
        user=p_args.user,
        max_rows=p_args.max_rows,
        outdir=p_args.outdir,
        with_calib=p_args.with_calib,
        count_only=p_args.count_only,
        metadata_only=p_args.metadata_only,
        collection=p_args.collection,
        cone=Cone.from_args(p_args, DEFAULT_RADIUS_DEG),
        filters=build_filters_phase3(p_args),
    )

    run_pipeline(downloader)

# -----#
# RAW
# -----#


def register_raw_subparser(
    subparsers: argparse._SubParsersAction,
    add_shared_args
) -> None:
    """Register raw CLI subcommand."""
    p = subparsers.add_parser("raw", help="Download ESO archive raw data")

    # RAW / Phase3 common args
    add_shared_args(p)

    p.add_argument("--target-name", help="Target name (metadata match)")
    p.add_argument("--ra", help="Right Ascension (degrees)")
    p.add_argument("--dec", help="Declination (degrees)")
    p.add_argument("--run-id", help="ESO Run ID (e.g. 090.C-0733(A))")
    p.add_argument("--instrument", help="Instrument name (e.g. FORS2)")
    p.add_argument("--file-cat", choices=["SCIENCE", "CALIB", "ACQUISITION"])
    p.add_argument("--start-date", help="Start date YYYY-MM-DD")
    p.add_argument("--end-date", help="End date YYYY-MM-DD")

    p.set_defaults(func=handle_raw)


def handle_raw(p_args: argparse.Namespace) -> None:
    """Handle raw CLI command."""
    downloader = RawDownloader(
        user=p_args.user,
        deauthenticate=p_args.deauthenticate,
        max_rows=p_args.max_rows,
        outdir=p_args.outdir,
        count_only=p_args.count_only,
        metadata_only=p_args.metadata_only,
        with_calib=p_args.with_calib,
        instrument=p_args.instrument,
        cone=Cone.from_args(p_args, DEFAULT_RADIUS_DEG),
        filters=build_filters_raw(p_args),
    )

    run_pipeline(downloader)

# -----#
# CLI
# -----#


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add shared CLI arguments."""
    parser.add_argument(
        "--user", help="ESO User Portal username; if provided, a password will be required")
    parser.add_argument("--deauthenticate", action="store_true",
                        help="Remove password from keyring. Use with --user <username>")
    parser.add_argument("--max-rows", type=int, default=100)
    parser.add_argument("--with-calib", choices=["raw", "processed"])
    parser.add_argument("--count-only", action="store_true",
                        help="Print the count of records and exit")
    parser.add_argument("--metadata-only", action="store_true",
                        help="Save a csv with the matching records and exit")
    parser.add_argument("--outdir", default="eso_downloads")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="eso-download",
                                     description="ESO archive downloader")
    subparsers = parser.add_subparsers(dest="<archive> = [raw | phase3]",
                                       required=True)

    register_raw_subparser(subparsers, add_common_args)
    register_phase3_subparser(subparsers, add_common_args)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    require_version(astroquery, ASTROQUERY_MIN_VER, ASTROQUERY_INSTALL)
    main()
