import pyrealsense2 as rs
import numpy as np
import cv2
from time import time
from matplotlib import pyplot as plt
from collections import deque
from numpy.fft import rfft, rfftfreq
from mkl_fft import rfft_numpy

'''
pip install pyrealsense2
pip install opencv-python
'''

def GetSpectrumFromImages(images_deque):

    # turn deque of images into one matrix for transforming
    images_3D = np.array([image.flatten() for image in images_deque])
    # images_3D = np.array(images_deque)
    # print(images_3D.shape)
    # print(images_3D[:,0].shape)
    # print(images_3D.shape[1])
    freq = rfftfreq(images_3D.shape[0],1.0/30.0)

    # apply fft on each pixel
    # pixel_spectra = [np.abs(rfft(images_3D[:,i]))**2 for i in range(images_3D.shape[1])]
    pixel_spectra = [np.abs(rfft(images_3D[:,i])) for i in range(images_3D.shape[1])]
    pixel_spectra = np.array(pixel_spectra)

    # print(pixel_spectra.shape)

    average_spectrum = np.mean(pixel_spectra,axis=0)
    average_spectrum = average_spectrum / sum(average_spectrum)
    # print(average_spectrum.shape)

    # print(average_spectrum)
    # plt.figure()
    # plt.plot(average_spectrum)
    # # plt.plot(pixel_spectra[0])
    # plt.show()
    
    return freq,average_spectrum

def GetSpectrumFromImagesMatrix(images_matrix, pixel_spectra=None):
    
    # get frequency values in spectral domain
    freq = rfftfreq(images_matrix.shape[0],1.0/30.0)

    # apply fft on each pixel
    # pixel_spectra = np.abs(rfft(images_matrix,axis=0))
    np.abs(rfft(images_matrix,axis=0),out=pixel_spectra)

    # get average spectrum across all pixels and normalize to sum to 1
    average_spectrum = np.mean( pixel_spectra, axis=(1,2) )
    average_spectrum = average_spectrum / sum(average_spectrum)

    return freq,average_spectrum

def GetSpectrumFromImagesMatrix2(images_matrix, complex_pixel_spectra=None, pixel_spectra_magnitudes=None):
    
    # get frequency values in spectral domain
    freq = rfftfreq(images_matrix.shape[0],1.0/30.0)

    # apply fft on each pixel
    # pixel_spectra = np.abs(rfft(images_matrix,axis=0))
    np.abs(rfft(images_matrix,axis=0),out=pixel_spectra)

    # get average spectrum across all pixels and normalize to sum to 1
    average_spectrum = np.mean( pixel_spectra, axis=(1,2) )
    average_spectrum = average_spectrum / sum(average_spectrum)

    return freq,average_spectrum


def GetRiemannSumFromSpectrum(x,y,xs,xe):
    return sum([y_i for x_i,y_i in zip(x,y) if (x_i >= xs and x_i <= xe)])


def GetImagesFromBag(bag_file_path, bag_timeout_ms = 500):

    try:

        colorizer = rs.colorizer()

        pipeline = rs.pipeline()
        config = rs.config()
        rs.config.enable_device_from_file(config, bag_file_path, repeat_playback=False)
        profile = pipeline.start(config).get_device().as_playback().set_real_time(False)
        
        depth_images_deque = deque()
        frame_numbers = []
        while True:
            frames = pipeline.wait_for_frames(timeout_ms=bag_timeout_ms)
            fn = frames.frame_number

            frame_numbers += [fn]
            cur_depth_frame = frames.get_depth_frame()
            # cur_color_frame = frames.get_color_frame()
            
            cur_depth_image = np.asanyarray(cur_depth_frame.get_data())
            # depth_images_deque.append(np.asanyarray(cur_depth_frame.get_data()))
    
    
            # cur_depth_color_image = np.asanyarray(colorizer.colorize(cur_depth_frame).get_data())
            # cv2.imwrite("plots2/" + str(fn).zfill(6) + ".png", cur_depth_color_image)

            depth_images_deque.append(cur_depth_image)

            # depth_images_deque.append(cur_)
            # print(len(depth_images_deque),fn)
            
    except Exception as e:
        print(e)
        if "arrive" in str(e):
            pipeline.stop()
            del(pipeline)
            del(profile)
            return np.array(frame_numbers),depth_images_deque
        else:
            raise(e)
        pass
    finally:
        return np.array(frame_numbers),depth_images_deque
