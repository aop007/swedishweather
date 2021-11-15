#!/usr/bin/env bash

CONDA_ENV='swenv'

conda create --prefix ./${CONDA_ENV} --file requirements.txt

conda activate "./${CONDA_ENV}/"