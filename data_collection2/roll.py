from copy import deepcopy
import numpy as np
import imageio

mydir = 'recordings/Sat Oct  3 11-53-08 2020/'
infrared_matrix = np.load(mydir+'infrared_matrix.npy')
# print(infrared_matrix)
i = 60

dummy_matrix = np.zeros_like(infrared_matrix)
for j in range(dummy_matrix.shape[0]):
    dummy_matrix[j,:,:] = np.full_like(dummy_matrix[j,:,:],j)
print(dummy_matrix)

rolled_matrix = np.roll(infrared_matrix,shift=-2*i,axis=0)
imageio.mimwrite(mydir+'infrared_video_rolled.mp4', rolled_matrix, fps=30)

print('---')
rolled_dummy_matrix = np.roll(dummy_matrix,shift=-60,axis=0)
# imageio.mimwrite(mydir+'infrared_video_rolled.mp4', infrared_matrix, fps=30)

print(rolled_dummy_matrix)
