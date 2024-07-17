from transformers import pipeline
import os
import glob
from PIL import Image
from torchvision import transforms as T

checkpoint = "vinvino02/glpn-nyu"
depth_estimator = pipeline("depth-estimation", model=checkpoint)

path = 'data/jumpingjacks_small/train'
files = glob.glob(os.path.join(path, '*.png'))

for file in files:
    image = Image.open(file)
    predictions = depth_estimator(image)
    pred_array = predictions['predicted_depth']
    pred_img = predictions['depth']

print(1)