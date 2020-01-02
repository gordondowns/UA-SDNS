import pyrealsense2 as rs
import numpy as np
import cv2
from time import time
from collections import deque

'''
pip install pyrealsense2
pip install opencv-python
'''


def calculateSD(depth_image1,depth_image2):

    # get pythagorean distance between the two images
    dist = np.abs(depth_image1-depth_image2)
    # alternatively, get pythagorean distance and mask out pixels where one of the frames has a 0 value
    # dist = np.where(np.logical_and(depth_image1 != 0, depth_image2 != 0), np.abs(depth_image1-depth_image2), 0)

    # apply Gaussian smoothing
    mod = cv2.GaussianBlur(dist, (9,9), 0)

    # calculate st dev test
    _, stDev = cv2.meanStdDev(mod)

    return stDev[0][0]

def GetStandardDeviationsFromBag(bag_file_path, frame_index_difference = 10, do_analysis_every_n_frames = 1, bag_timeout_ms = 500, filter=False):

    try:
        pipeline = rs.pipeline()
        config = rs.config()
        rs.config.enable_device_from_file(config, bag_file_path, repeat_playback=False)
        profile = pipeline.start(config).get_device().as_playback().set_real_time(False)
        
        depth_frames_deque = deque()
        SDs = []
        FNs = []
        all_frame_numbers = []
        frames_since_last_analysis = 0

        if filter:
            spatial = rs.spatial_filter()
            decimation = rs.decimation_filter()
            hole_filling = rs.hole_filling_filter()
            hole_filling.set_option(rs.option.holes_fill, 2)

        while True: 
            frames = pipeline.wait_for_frames(timeout_ms=bag_timeout_ms)
            fn = frames.frame_number
            all_frame_numbers += [fn]
            frames_since_last_analysis += 1
            cur_depth_frame = frames.get_depth_frame()

            if filter:
                cur_depth_frame = decimation.process(cur_depth_frame)
                cur_depth_frame = spatial.process(cur_depth_frame)
                cur_depth_frame = hole_filling.process(cur_depth_frame)

            depth_frames_deque.append(cur_depth_frame)

            if len(depth_frames_deque) > frame_index_difference:
                cur_depth_image = np.asanyarray(cur_depth_frame.get_data())
                past_depth_image = np.asanyarray(depth_frames_deque.popleft().get_data())
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
            return np.array(all_frame_numbers),np.array(FNs),np.array(SDs)
        else:
            raise(e)
        pass
    finally:
        return np.array(all_frame_numbers),np.array(FNs),np.array(SDs)
