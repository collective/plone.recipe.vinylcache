#!/bin/sh
rm -r ./lib ./include ./local ./bin
python3 -m venv .
./bin/pip install --upgrade -r requirements.txt
./bin/buildout
