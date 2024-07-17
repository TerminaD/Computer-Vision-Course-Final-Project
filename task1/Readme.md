# Readme

## 1. Installation

This code has been run on a MacBook Pro with M1 Pro and an Ubuntu 20.04 machine with CUDA 11.8 and a Nvidia RTX 4090 with 24GB of VRAM.

Simply create a Conda environment with:

```bash
conda create -f environment.yml
conda activate cv-nerf
```

## 2. Training

Use

```
python main.py --train
```

You can specify hyperparamers including but not restricted to the dataset path, the batch size, the positional encoding frequency, etc. The command above will list all possible arguments.

## 3. Testing

Use

```
python main.py --test
```

Much like in training, you can also specify arguments. 
