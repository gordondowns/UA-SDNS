import pyrealsense2 as rs
import numpy as np
import cv2
from time import time
from matplotlib import pyplot as plt
from collections import deque

'''
pip install pyrealsense2
pip install opencv-python
'''


def calculateSD(depth_image1,depth_image2):

    # get pythagorean distance between the two images
    # mask out pixels where one of the frames has a 0 value
    dist = np.where(np.logical_and(depth_image1 != 0, depth_image2 != 0), np.abs(depth_image1-depth_image2), 0)
    # dist = np.abs(depth_image1-depth_image2)
    
    # apply Gaussian smoothing
    mod = cv2.GaussianBlur(dist, (9,9), 0)

    # calculate st dev test
    _, stDev = cv2.meanStdDev(mod)

    return stDev[0][0]

def GetStandardDeviationsFromBag(bag_file_path, frame_index_difference = 10, do_analysis_every_n_frames = 1, bag_timeout_ms = 500):

    try:
        pipeline = rs.pipeline()
        config = rs.config()
        rs.config.enable_device_from_file(config, bag_file_path, repeat_playback=False)
        profile = pipeline.start(config).get_device().as_playback().set_real_time(False)
        
        depth_images_deque = deque()
        depth_images_list = []
        color_images_list = []
        SDs = []
        FNs = []
        all_frame_numbers = []
        frames_since_last_analysis = 0
        first_frame = True

        while True:
            frames = pipeline.wait_for_frames(timeout_ms=bag_timeout_ms)
            fn = frames.frame_number
            if first_frame:
                timestamp_start = frames.timestamp
                first_frame = False
            else:
                timestamp_end = frames.timestamp
            # print(fn)
            all_frame_numbers += [fn]
            frames_since_last_analysis += 1
            cur_depth_frame = frames.get_depth_frame()
            cur_color_frame = frames.get_color_frame()
            cur_depth_image = np.asanyarray(cur_depth_frame.get_data())
            cur_color_image = np.asanyarray(cur_color_frame.get_data())
            
            depth_images_deque.append(cur_depth_image)
            color_images_list = [cur_color_image]
            depth_images_list = [cur_depth_image]
            
            if len(depth_images_deque) > frame_index_difference:
                past_depth_image = depth_images_deque.popleft()
                if frames_since_last_analysis >= do_analysis_every_n_frames:
                    SDs += [calculateSD(cur_depth_image,past_depth_image)]
                    FNs += [fn]
                    frames_since_last_analysis = 0
    except Exception as e:
        # print(e)
        if "arrive" in str(e):
            pipeline.stop()
            del(pipeline)
            del(profile)
            return np.array(all_frame_numbers),depth_images_list,color_images_list,np.array(FNs),np.array(SDs),timestamp_end-timestamp_start
        else:
            raise(e)
        pass
    finally:
        return np.array(all_frame_numbers),np.array(depth_images_list),np.array(color_images_list),np.array(FNs),np.array(SDs),timestamp_end-timestamp_start
