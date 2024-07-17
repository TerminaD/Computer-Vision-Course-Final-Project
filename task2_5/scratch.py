from utils.positional_encoding import PositionalEncoding
import torch

encoder = PositionalEncoding(5)

for i in [-0.7, 0.7]:
    print(encoder(i * torch.ones(1, 1)))
