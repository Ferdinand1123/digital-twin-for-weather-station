#!/bin/sh
conda init bash
. ~/.bashrc 
conda activate crai
exec gunicorn -b :3000 --access-logfile - --error-logfile - app:app