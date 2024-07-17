import torch


class NeRFMSEDepthLoss(torch.nn.Module):
    def __init__(self):
        super().__init__()
        
    def forward(self, gt, pred_coarse, pred_fine, gt_depths, pred_depths):
        return torch.mean((gt-pred_coarse) ** 2) + \
               torch.mean((gt-pred_fine) ** 2) + \
               torch.mean((gt_depths-pred_depths) ** 2)
    
    