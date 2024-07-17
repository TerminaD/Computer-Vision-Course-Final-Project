import torch.nn as nn


class DeformationField(nn.Module):
    def __init__(self,
                 in_channels_xyz=60,
                 in_channels_time=16):
        super().__init__()
        self.in_channels_xyz = in_channels_xyz
        self.in_channels_time = in_channels_time
        
        self.funcs = nn.Sequential(
            nn.Linear(in_channels_xyz+in_channels_time, 256),
			nn.ReLU(),
            nn.Linear(256, 256),
			nn.ReLU(),
            nn.Linear(256, 256),
			nn.ReLU(),
            nn.Linear(256, 256),
			nn.ReLU(),
            nn.Linear(256, 256),
			nn.ReLU(),
            nn.Linear(256, 256),
			nn.ReLU(),
            nn.Linear(256, 64),
			nn.ReLU(),
            nn.Linear(64, 3),
            nn.Tanh())
        
    def forward(self, x):
        return 2*self.funcs(x)
        