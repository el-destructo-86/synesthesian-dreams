#!/bin/bash

python train.py --epochs=300 --batch_size=256 --nz=100 --use_gpu \
                --model_dir=first_model --model_name=first_model \
                --save_model_every=50 --check_gen_every=10
