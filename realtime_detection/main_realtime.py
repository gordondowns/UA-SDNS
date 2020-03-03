# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 21:32:08 2020

@author: guard
"""
import numpy as np
import time
# from RunMotionDetection import GetStandardDeviationsFromBag, calculateSD
from RunSeizureDetection import GetSpectrumFromImagesMatrix, GetRiemannSumFromSpectrum
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from glob import glob
from pynput import keyboard
from matplotlib import pyplot as plt
from collections import deque
from sklearn.linear_model import LogisticRegression

'''
pip install pyrealsense2
pip install opencv-python
pip install pynput
conda install pytorch torchvision cudatoolkit=10.1 -c pytorch
'''


CAMERA_FRAMERATE = 30 #fps
SIZE_OF_WINDOW = 30 #frames, must be even
CALIBRATION_TIME = 5.0 #sec
MIN_SEIZURE_FREQUENCY = 4.0 #Hz
MAX_SEIZURE_FREQUENCY = 8.0 #Hz
SEIZURE_POWER_THRESHOLD = 0.10 #unitless
use_filters = False
save_calibration_plot = True
show_calibration_plot = False
save_motion_plots = True
save_no_motion_plots = True
plot_dir_path_motion = 'plots_with_motion/'
plot_dir_path_no_motion = 'plots_without_motion/'
save_calibration_bag = False
show_spectral_plots = True
save_spectral_plots = False
spectral_plot_dir = 'output_spectra/'
# video_source = 'camera'
video_source = 'bag'
source_bag_file_path = '../../sample bag data/Alternating motion every 15 for 2 mins incremental motion-002.bag'
ML_MODEL = '3 param'
# ML_MODEL = 'logistic regression'
# ML_MODEL = 'ANN 1 window'
# ML_MODEL = 'ANN 10 windows'


def startVideoStream(runimageanalysis_queue,keypress_queue):
    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    
    if use_filters:
        hole_filling = rs.hole_filling_filter()
        hole_filling.set_option(rs.option.holes_fill, 2)

    # Start streaming
    if video_source == 'camera':
        print("Starting camera feed",flush=True)
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
        # config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, CAMERA_FRAMERATE)
        pipeline.start(config)
    elif video_source == 'bag':
        print("Starting camera feed",flush=True)
        
        rs.config.enable_device_from_file(config, source_bag_file_path)
        # pipeline = rs.pipeline()
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
        pipeline.start(config)

        # rs.config.enable_device_from_file(config, source_bag_file_path, repeat_playback=False)
        # profile = pipeline.start(config).get_device().as_playback().set_real_time(True)
        # pipeline.start(config).get_device().as_playback().set_real_time(True)
    else:
        del(pipeline)
        del(config)
        raise(Exception("video_source must be either 'camera' or 'bag'"))
    
    fn = 0
    loop = 0
    fn_prev = 0
    
    try:
        while True:
            # First, check if user pressed key to stop recording
            try:
                # Queue.get(block=False) throws exception if nothing in queue
                message = keypress_queue.get(block=False)
                if message == 'stop':
                    print('stopping recording bag files')
                    break
            except:
                pass
            # Wait for a coherent pair of frames: depth and color
            frames = pipeline.wait_for_frames(timeout_ms=30000)
            depth_frame = frames.get_depth_frame()
            if use_filters:
                depth_frame = hole_filling.process(depth_frame)
            
            #color_frame = frames.get_color_frame()
            #print('sending to motion detection', flush = True)
            depth_image = np.asanyarray(depth_frame.get_data())

            loop += 1
            fn = frames.frame_number
            frame_diff = fn - fn_prev
            if frame_diff > 0:
                runimageanalysis_queue.put(depth_image)
            if frame_diff > 1:
                print("dropped",frame_diff-1,"frames before frame",fn)
            if loop == 10:
                print("Current frame capture: " + str(fn))
                loop = 0
            fn_prev = fn


    finally:
        # Stop streaming if exception thrown
        pipeline.stop()
        del(pipeline)
        del(config)

def on_activate_f(startvideostream_queue):
    print('f key pressed')
    startvideostream_queue.put('stop')

def keyPressMonitor(startvideostream_queue):
    # Collect events until released
    with keyboard.GlobalHotKeys({
            'f': lambda: on_activate_f(startvideostream_queue)
            }) as h:
        h.join()

class ThreeParamClassifier:
    def __init__(self,freq_min,freq_max,power_threshold):
        self.freq_min = freq_min
        self.freq_max = freq_max
        self.power_threshold = power_threshold
    def detect_seizure(self,x,y):
        rsum = GetRiemannSumFromSpectrum(x,y,self.freq_min,self.freq_max)
        return rsum > self.power_threshold


def GetClassifier(model):
    if model == '3 param':
        clf = ThreeParamClassifier(MIN_SEIZURE_FREQUENCY,MAX_SEIZURE_FREQUENCY,SEIZURE_POWER_THRESHOLD)
    elif model == 'logistic regression':
        clf = LogisticRegression().fit(
            [[0.6509689 , 0.02363854, 0.0236765 , 0.02345174, 0.02362207, 0.0233341
             ,0.02347176, 0.02348028, 0.02340704, 0.02320979, 0.02333202, 0.02336428
             ,0.02344779, 0.02332139, 0.02318808, 0.02108571],
            [ 0.6046337 , 0.02686309, 0.02733968, 0.02642311, 0.02699386, 0.02669705
             ,0.03173579, 0.02689421, 0.02587553, 0.02484171, 0.02590532, 0.02585418
             ,0.02606342, 0.0256851 , 0.02600933, 0.02218497]],
             [0,1]
        )
        clf.detect_seizure = clf.predict
    elif model == 'ANN 1 window':
        pass
    elif model == 'ANN 10 windows':
        pass
    return clf


def runImageAnalysis(startvideostream_queue,notification_queue,):
    
    depth_images = np.zeros([SIZE_OF_WINDOW,720,1280],dtype='float32')
    spectra = np.zeros([int(SIZE_OF_WINDOW/2+1),720,1280],dtype='float32')
    cur_index = 0
    clf = GetClassifier(ML_MODEL)
    seizure_detected = False

    while True:
        depth_images[cur_index,:,:] = startvideostream_queue.get()

        if cur_index < SIZE_OF_WINDOW-1:
            cur_index += 1
        else:
            print("    running seizure detection...")
            t0 = time.time()

            x,y = GetSpectrumFromImagesMatrix(depth_images,spectra)
            # x,y = range(31), [1.0/31.0]*31
            
            if clf.detect_seizure(x,y):
                notification_queue.put("")
                seizure_detected = True
            else:
                print("        no seizure detected")
                seizure_detected = False

            cur_index = 0
            elapsed_time = time.time()-t0
            print("    seizure detection took {0:.1f} frames ({1:.2f} sec)".format(elapsed_time*30,elapsed_time))
             
            if show_spectral_plots or save_spectral_plots:
                plt.figure(1)
                plottime = "{0:.1f}".format(time.time())
                plt.title(plottime+': Seizure detected: '+str(seizure_detected))
                plt.bar(x[1:],y[1:],width=(x[1]-x[0])*0.8,color='blue',label='average FFT across all pixels')
                plt.legend()
                if save_spectral_plots:
                    plt.savefig(spectral_plot_dir+'spectrum'+plottime+'.png')
                if show_spectral_plots:
                    plt.show()
                plt.close()



def sendNotification(runimageanalysis_queue):
    while True:
        get = runimageanalysis_queue.get()
        # once we can interface with the notification app, change this to notify the caregivers via the smartphone app
        print("        SEIZURE DETECTED",get)
        


def calibrate_SDs(calibration_bag_path,calibration_plot_path,verbose=True):
    print("beginning calibration",flush=True)

    if use_filters:
        hole_filling = rs.hole_filling_filter()
        hole_filling.set_option(rs.option.holes_fill, 2)

    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
    # config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, CAMERA_FRAMERATE)
    config.enable_record_to_file(calibration_bag_path)

    # Start streaming
    if verbose:
        print("creating calibration bag file "+calibration_bag_path,flush=True)
    pipeline.start(config)
    t0 = time.time()
    
    try:
        while True:
            # Wait for a coherent pair of frames: depth and color
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            if use_filters:
                depth_frame = hole_filling.process(depth_frame)

            # color_frame = frames.get_color_frame()
            # if not depth_frame or not color_frame:
            if not depth_frame:
                continue
            if (time.time() - t0) >= CALIBRATION_TIME:
                if verbose:
                    print("saving calibration bag file "+calibration_bag_path,flush=True)
                break
    finally:
        # Stop streaming
        pipeline.stop()
        del(pipeline)
        del(config)
    #Get Standard Deviations for calibration
    if verbose:
        print("Calculating SDs for calibration")
    _,FNs,SDs = GetStandardDeviationsFromBag(calibration_bag_path,10,10,filter=use_filters)
    if verbose:
            print("SDs calculated for calibration")
    big = np.partition(np.array(SDs), -5)[-5]
    SD_thresh = big
    if verbose:
        print("Threshold for calibration is " + str(SD_thresh))
    bag_file_nickname = 'Calibration SDs'
    plt.figure(1)
    plt.title(bag_file_nickname)
    plt.plot(FNs,SDs,color='blue',linewidth=1.0,label='Intel motion detection algorithm')
    plt.axhline(y=SD_thresh)
    plt.legend()
    if save_calibration_plot:
        plt.savefig(plot_dir_path_no_motion+bag_file_nickname+'.png')
    if show_calibration_plot:
        plt.show()
    plt.close()

    if not save_calibration_bag:
        del(calibration_bag_path)

    return SD_thresh


def main():

    # time.sleep(1)
    # calibration_plot_path = plot_dir_path_no_motion+'Calibration SDs'+'.png'
    # calibration_bag_path = 'new_bags/' + 'Calibration' + '.bag'
    # STANDARD_DEVIATION_THRESHOLD = calibrate_SDs(calibration_bag_path,calibration_plot_path)
    # STANDARD_DEVIATION_THRESHOLD = 26100
    # STANDARD_DEVIATION_THRESHOLD = 0

    # initialize multiprocessing queues
    startvideostream_runimageanalysis_queue = Queue()
    runimageanalysis_notification_queue = Queue()
    key_startvideostream_queue = Queue()

    # declare multiprocessing processes, and connect with queues
    startvideostream_process = Process(target=startVideoStream,args=(startvideostream_runimageanalysis_queue,key_startvideostream_queue,))
    runimageanalysis_process = Process(target=runImageAnalysis,args=(startvideostream_runimageanalysis_queue,runimageanalysis_notification_queue,))
    notification_process = Process(target=sendNotification,args=(runimageanalysis_notification_queue,))
    # key_process = Process(target=keyPressMonitor,args=(key_startvideostream_queue,))

    # start multiprocessing processes
    startvideostream_process.start()
    runimageanalysis_process.start()
    notification_process.start()
    # key_process.start()

    # end multiprocessing processes if they finish
    # they won't finish (barring exceptions), since they're all infinite while loops.
    startvideostream_process.join()
    runimageanalysis_process.join()
    notification_process.join()
    # key_process.join()


if __name__ == '__main__':
    main()
