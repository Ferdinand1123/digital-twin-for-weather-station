#!/bin/bash
#SBATCH --job-name=dummy_test_job
#SBATCH --partition=compute
#SBATCH --ntasks=64
#SBATCH --mem=0
#SBATCH --time=07:30:00
#SBATCH --mail-type=FAIL
#SBATCH --account=uo1075
#SBATCH --output=%j.out

module load python3

python3 demo.py
