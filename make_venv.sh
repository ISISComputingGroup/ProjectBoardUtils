#!/bin/sh
PYDIR=./venv
rm -fr "${PYDIR}"
python -m venv ${PYDIR}
source $PYDIR/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
