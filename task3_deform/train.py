from models.d_nerf import D_NeRF
from models.d_render import render_rays, render_image
from utils.dataset import BlenderDataset
from utils.psnr import psnr_func
from utils.loss import NeRFMSELoss

import os
import argparse
import datetime

from tqdm import tqdm
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter


def parse_args(debug=False):
    if debug:
        parser = argparse.ArgumentParser()
        parser.add_argument('-d', '--data', type=str, default='data/jumpingjacks_small',
                            help='Path to collection of images to fit NeRF on. Should follow COLMAP format.')
        parser.add_argument('-c', '--ckpt', type=str, default='debug4',
                            help='Name of checkpoint to save to. Defaults to timestamp.')
        parser.add_argument('-e', '--epoch', type=int, default=2)
        parser.add_argument('-b', '--batch_size', type=int, default=64)
        parser.add_argument('--xyz_L', type=int, default=10, 
                            help='Parameter L in positional encoding for xyz.')
        parser.add_argument('--dir_L', type=int, default=4, 
                            help='Parameter L in positional encoding for direction.')
        parser.add_argument('--sample_num_coarse', type=int, default=64, 
                            help='How many points to sample on each ray for coarse model.')
        parser.add_argument('--sample_num_fine', type=int, default=128, 
                            help='How many points to sample on each ray for fine model.')
        parser.add_argument('-t', '--test_every', type=int, default=1,
                            help='Performs testing after we\'ve trained for this many epochs.')
        parser.add_argument('--test_in_training', default=True,
                            help='Perform testing during training')
        parser.add_argument('--lr', type=float, default=1e-3,
                            help='Learning rate')
        parser.add_argument('-l', '--length', type=int, default=200,
                            help='Length of images. Currently only support square images.')
        args = parser.parse_args()
        
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('-d', '--data', type=str, default='data/jumpingjacks_small',
                            help='Path to collection of images to fit NeRF on. Should follow COLMAP format.')
        parser.add_argument('-c', '--ckpt', type=str, default='debug',
                            help='Name of checkpoint to save to. Defaults to timestamp.')
        parser.add_argument('-e', '--epoch', type=int, default=100)
        parser.add_argument('-b', '--batch_size', type=int, default=64)
        parser.add_argument('--xyz_L', type=int, default=10, 
                            help='Parameter L in positional encoding for xyz.')
        parser.add_argument('--dir_L', type=int, default=4, 
                            help='Parameter L in positional encoding for direction.')
        parser.add_argument('--sample_num_coarse', type=int, default=64, 
                            help='How many points to sample on each ray for coarse model.')
        parser.add_argument('--sample_num_fine', type=int, default=128, 
                            help='How many points to sample on each ray for fine model.')
        parser.add_argument('-t', '--test_every', type=int, default=1, 
                            help='Performs testing after we\'ve trained for this many epochs.')
        parser.add_argument('--test_in_training', action='store_true',
                            help='Perform testing during training')
        parser.add_argument('--lr', type=float, default=1e-3,
                            help='Learning rate')
        parser.add_argument('-l', '--length', type=int, default=200,
                            help='Length of images. Currently only support square images.')
        args = parser.parse_args()
        
    return args


def train() -> None:
    debug = True
    
    args = parse_args(debug)
    
    if not args.ckpt:
        now = datetime.datetime.now()
        args.ckpt = now.strftime("%m-%d-%H-%M-%S")
    
    writer = SummaryWriter()
    
    if torch.cuda.is_available():
        device = 'cuda:0'
    # elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
    #     device = 'mps'
    else:
        device = 'cpu'
    device = torch.device(device)
    print(f"Device is {device}")
    
    trainset = BlenderDataset(root_dir=args.data, 
                              split='train', 
                              img_wh=(args.length, args.length))
    trainloader = DataLoader(trainset,
                             shuffle=True,
                             num_workers=8, 
                             batch_size=args.batch_size,
                             pin_memory=True)
    testset = BlenderDataset(root_dir=args.data, 
                             split='test', 
                             img_wh=(args.length, args.length))
    
    model_coarse = D_NeRF(in_channels_xyz=3, 
                          in_channels_dir=3,
                          in_channels_time=1,
                          sample_num=args.sample_num_coarse,
                          xyz_L=args.xyz_L,
                          dir_L=args.dir_L)
    model_fine = D_NeRF(in_channels_xyz=3, 
                        in_channels_dir=3,
                        in_channels_time=1,
                        sample_num=args.sample_num_fine+args.sample_num_coarse,
                        xyz_L=args.xyz_L,
                        dir_L=args.dir_L)
    model_coarse.to(device)
    model_fine.to(device)
    
    all_params = list(model_coarse.parameters()) + list(model_fine.parameters())
    optimizer = torch.optim.Adam(all_params, lr=args.lr)
    nerf_criterion = NeRFMSELoss()
    mse_criterion = nn.MSELoss()
    
    os.makedirs(f'checkpoints/{args.ckpt}/coarse', exist_ok=True)
    os.makedirs(f'checkpoints/{args.ckpt}/fine', exist_ok=True)
    os.makedirs(f'renders/{args.ckpt}/train', exist_ok=True)
    
    for e in range(args.epoch):
        print(f"epoch:{e}")
        cum_loss = 0.0
        for sample in tqdm(trainset,desc="raying",leave=False):
            rays = sample['rays'].to(device)
            # gt_rgbs = sample['rgbs'].to(device)
            times = sample['times'].to(device)
            
            optimizer.zero_grad()

            pred_img, pred_img_coarse = render_image(rays=rays,
                                    batch_size=args.batch_size,
                                    img_shape=(args.length, args.length),
                                    times=times,
                                    sample_num_coarse=args.sample_num_coarse,
                                    sample_num_fine=args.sample_num_fine,
                                    nerf_coarse=model_coarse,
                                    nerf_fine=model_fine,
                                    device=device)
            gt_img = sample['rgbs'].reshape(args.length, args.length, 3).to(device)
            
            loss = nerf_criterion(gt_img, pred_img_coarse, pred_img)
            loss.requires_grad_(True) 
            print(loss)
            loss.backward()
            cum_loss += loss
            
            optimizer.step()

        cum_loss /= len(trainloader)
        writer.add_scalar('Loss/train', cum_loss, e)
        print(cum_loss.item())
        
        # Perform testing periodically
        if args.test_in_training and e % args.test_every == 0:
            with torch.no_grad():
                print("Testing...")
                sample = testset[0]
                pred_img, _ = render_image(rays=sample['rays'],
                                        batch_size=args.batch_size,
                                        img_shape=(args.length, args.length),
                                        times=sample['times'],
                                        sample_num_coarse=args.sample_num_coarse,
                                        sample_num_fine=args.sample_num_fine,
                                        nerf_coarse=model_coarse,
                                        nerf_fine=model_fine,
                                        device=device)
                gt_img = sample['rgbs'].reshape(args.length, args.length, 3).to(device)
                
                loss = mse_criterion(gt_img, pred_img)
                psnr = psnr_func(gt_img, pred_img)
                
                writer.add_scalar('MSE/test', loss, e)
                writer.add_scalar('PSNR/test', psnr, e)
                
                torch.save(model_coarse.state_dict(), f"checkpoints/{args.ckpt}/coarse/{e}.pth")
                torch.save(model_fine.state_dict(), f"checkpoints/{args.ckpt}/fine/{e}.pth")
                plt.imsave(f'renders/{args.ckpt}/train/{e}.png', torch.clip(pred_img, 0, 1).cpu().numpy())
    
    torch.save(model_coarse.state_dict(), f"checkpoints/{args.ckpt}/coarse/final.pth")
    torch.save(model_fine.state_dict(), f"checkpoints/{args.ckpt}/fine/final.pth") 
                
    writer.flush()
    

if __name__ == '__main__':
    train()
    