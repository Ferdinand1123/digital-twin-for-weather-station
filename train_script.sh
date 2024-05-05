#!/usr/bin/env bash

#SBATCH -J crai-train
#SBATCH --output /home/k/k203179/digital-twin-for-weather-station/slurm_logs/crai_crai-train_%j.log
#SBATCH -p gpu
#SBATCH -A bm1159
#SBATCH --time=12:00:00
#SBATCH --mem=485G
#SBATCH --exclusive
#SBATCH --constraint a100_80

cd /home/k/k203179/digital-twin-for-weather-station
module load python3

# Initialize Conda (add this line)
eval "$(conda shell.bash hook)"

conda activate /home/k/k203179/.conda/envs/crai

python -m climatereconstructionai.train --load-from-file /tmp/tmpin99jp0e/train_args.txt 
