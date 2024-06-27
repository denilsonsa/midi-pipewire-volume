#!/bin/sh
#
# Convenience script for running this tool without installing it.
#
# Usage:
#   ./run.sh
#
# WILL NOT WORK if the current working directory is different.

if [ ! -d midipwvol ] ; then
	echo 'Please cd into this repository directory before running ./run.sh'
	exit 1
fi

if [ ! -d venv ] ; then
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
fi


exec ./venv/bin/python -m midipwvol
