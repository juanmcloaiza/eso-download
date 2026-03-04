# eso-download

Lightweight command-line utility to query and download ESO Archive raw and Phase3 data.

## Install

```
pip install eso-download
```
- Requires `python>=3.10`

## General Usage


### Phase3

```
$ eso-download phase3 -h
```
```
usage: eso-download phase3 [-h] [--user USER] [--deauthenticate] [--max-rows MAX_ROWS] [--with-calib {raw,processed}]
                           [--count-only] [--metadata-only] [--outdir OUTDIR] [--target-name TARGET_NAME] [--ra RA]
                           [--dec DEC] [--proposal-id PROPOSAL_ID] [--instrument INSTRUMENT] [--collection COLLECTION]
                           [--facility FACILITY] [--release-date-min RELEASE_DATE]
                           [--release-date-max RELEASE_DATE] [--publication-date-min PUBLICATION_DATE]
                           [--publication-date-max PUBLICATION_DATE]

options:
  -h, --help            show this help message and exit
  --user USER           ESO User Portal username; if provided, a password will be required
  --deauthenticate      Remove password from keyring. Use with --user <username>
  --max-rows MAX_ROWS
  --with-calib {raw,processed}
  --count-only          Print the count of records and exit
  --metadata-only       Save a csv with the matching records and exit
  --outdir OUTDIR
  --target-name TARGET_NAME
                        Target name (metadata match)
  --ra RA               Right Ascension in degrees
  --dec DEC             Declination in degrees
  --proposal-id PROPOSAL_ID
                        ESO Proposal ID (e.g. 094.B-0345(A))
  --instrument INSTRUMENT
                        Instrument name (e.g. MUSE)
  --collection COLLECTION
                        Observation collection name (e.g. MUSE)
  --facility FACILITY   Facility name (e.g. ESO-VLT-U4)
  --release-date-min RELEASE_DATE
                        Release date range start (YYYY-MM-DD)
  --release-date-max RELEASE_DATE
                        Release date range end (YYYY-MM-DD)
  --publication-date-min PUBLICATION_DATE
                        Publication date range start (YYYY-MM-DD)
  --publication-date-max PUBLICATION_DATE
                        Publication date range end (YYYY-MM-DD)
```


### Raw

```
$ eso-download raw -h
```


```
usage: eso-download raw [-h] [--user USER] [--deauthenticate] [--max-rows MAX_ROWS] [--with-calib {raw,processed}]
                        [--count-only] [--metadata-only] [--outdir OUTDIR] [--target-name TARGET_NAME] [--ra RA] [--dec DEC]
                        [--run-id RUN_ID] [--instrument INSTRUMENT] [--file-cat {SCIENCE,CALIB,ACQUISITION}]
                        [--start-date START_DATE] [--end-date END_DATE]

options:
  -h, --help            show this help message and exit
  --user USER           ESO User Portal username; if provided, a password will be required
  --deauthenticate      Remove password from keyring. Use with --user <username>
  --max-rows MAX_ROWS
  --with-calib {raw,processed}
  --count-only          Print the count of records and exit
  --metadata-only       Save a csv with the matching records and exit
  --outdir OUTDIR
  --target-name TARGET_NAME
                        Target name (metadata match)
  --ra RA               Right Ascension (degrees)
  --dec DEC             Declination (degrees)
  --run-id RUN_ID       ESO Run ID (e.g. 090.C-0733(A))
  --instrument INSTRUMENT
                        Instrument name (e.g. FORS2)
  --file-cat {SCIENCE,CALIB,ACQUISITION}
  --start-date START_DATE
                        Start date YYYY-MM-DD
  --end-date END_DATE   End date YYYY-MM-DD

  ```

  ---

## Usage examples

### Raw archive

```
$ eso-download raw --help
```

```
$ eso-download raw --user <user> \
        --run-id "090.C-0733(A)" \
        --instrument FORS2
```

```
$ eso-download raw --user <user> \
        --ra 129.0629 --dec -26.4093 \
        --max-rows 20
```

```
$ eso-download raw --run-id '090.C-0733(A)' \
        --instrument FORS2 \
        --start-date 2013-01-01 --end-date 2013-04-01 \
        --file-cat SCIENCE \
        --max-rows 30 --metadata-only
```

### Phase3 archive

```
$ eso-download phase3 --help
```

```
$ eso-download phase3 --user <user> \
        --proposal-id "094.B-0345(A)" \
        --collection MUSE
```

```
$ eso-download phase3 --user <user> \
        --target-name "NGC 253"
```

```
$ eso-download phase3 --proposal-id '275.A-5060(A)' \
        --instrument FORS2 \
        --target-name 'GDS J033223' \
        --ra 53.1 --dec -27.73\
        --publication-date-min 2014-07-11 --publication-date-max 2014-07-12 \
        --facility ESO-VLT-U1 \
        --max-rows 30 --metadata-only
```

- **public vs proprietary data** - While all Phase3 metadata is available for all users
--authenticated and unauthenticated alike, data within the proprietary period is restricted.
To query metadata and files available to the public, `--release-date-max` must be set to the current date, e.g.,

    ```
    $ eso-download phase3 --collection MUSE-DEEP --release-date-max 2026-03-04 --max-rows 3
    Querying ESO archive...
    Found 3 datasets...
    Records written to eso_downloads/query_results.csv
    INFO: Downloading datasets ... [astroquery.eso.core]
    INFO: Downloading 3 files ... [astroquery.eso.core]
    ...
    ```

    Requesting data within the proprietary period (`--release-date-min` = "today") will result in Access denied errors as shown below, unless the user is authenticated as the owner of the data.

    ```
    $ eso-download phase3 --collection MUSE-DEEP --release-date-min 2026-03-04 --max-rows 3
    Querying ESO archive...
    Found 3 datasets...
    Records written to eso_downloads/query_results.csv
    ...
    ERROR: Access denied to https://dataportal.eso.org/dataPortal/file/ADP.2025-07-21T21:36:53.034 [astroquery.eso.core]
    ERROR: Access denied to https://dataportal.eso.org/dataPortal/file/ADP.2025-08-18T10:18:10.295 [astroquery.eso.core]
    ERROR: Access denied to https://dataportal.eso.org/dataPortal/file/ADP.2025-08-27T07:19:38.715 [astroquery.eso.core]
    ```

### Common options - count available records and query metadata only

```
$ eso-download raw --count-only
```

```
$ eso-download phase3 --metadata-only
```


### Authenticate / Deauthenticate

-  To download proprietary data and metadata available only to user <username>:

    ```
    $ eso-download [raw|phase3] --user <username>
    ```
    A password is required if not yet unauthenticated.


- To delete a saved password (deauthenticate):
    ```
    $ eso-download [raw|phase3] --user <username> --deauthenticate
    ```

    Password for `<username>` will need to be re-entered next time.

---
