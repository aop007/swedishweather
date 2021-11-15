#!/usr/bin/env bash

cat requirements_pip.txt | xargs -n 1 -L 1 pip install