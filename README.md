TODO - real readme

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
        --publication-date-start 2014-07-11 --publication-date-end 2014-07-12 \
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