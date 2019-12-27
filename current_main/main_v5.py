import numpy as np
import time
from matplotlib import pyplot as plt
from glob import glob
from RunMotionDetection import GetStandardDeviationsFromBag
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from RunMotionDetection import GetStandardDeviationsFromBag
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

'''
pip install pyrealsense2
pip install opencv-python
'''

CAMERA_FRAMERATE = 30
SECONDS_PER_RECORDING = 10.0
STANDARD_DEVIATION_THRESHOLD = 27800
NUM_POINTS_ABOVE_THRESHOLD_SOUGHT = 10
bagfiles_dir_path_new = 'new_bags/'
bagfiles_dir_path_motion = 'bags_with_motion/'


def saveBagFile(runmotiondetection_queue):
    while True:
        #Get current time to name the file
        Date = time.asctime(time.localtime(time.time())).replace(':','-')
        # file_path = bagfiles_dir_path_new + Date + '.bag'
        file_path = bagfiles_dir_path_new + str(int(time.time())) + '.bag'
        
        # Configure depth and color streams
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, CAMERA_FRAMERATE)
        config.enable_record_to_file(file_path)
        
        # Start streaming
        pipeline.start(config)
        t0 = time.time()
        
        try:
            while True:
                # Wait for a coherent pair of frames: depth and color
                frames = pipeline.wait_for_frames()
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                if not depth_frame or not color_frame:
                    continue
                if (time.time() - t0) >= SECONDS_PER_RECORDING:
                    print("saving bag file to "+file_path,flush=True)
                    break
        finally:
            # Stop streaming
            pipeline.stop()
            del(pipeline)
            del(config)
            runmotiondetection_queue.put(file_path)

def runMotionDetection(savebagfile_queue,sendfiletocloud_queue,deletefile_queue):
    while True:
        file_path = savebagfile_queue.get()
        print("    running motion detection on "+file_path,flush=True)

        _,_,SDs = GetStandardDeviationsFromBag(file_path,10,10)
        count = sum( SDs > STANDARD_DEVIATION_THRESHOLD)
        if count > NUM_POINTS_ABOVE_THRESHOLD_SOUGHT:
            print("    motion detected",flush=True)
            sendfiletocloud_queue.put(file_path)
        else:
            print("    NO motion detected",flush=True)
            deletefile_queue.put(file_path)

def sendFileToCloud(runmotiondetection_queue):
    # Send file to cloud by moving it into a folder that syncs with Dropbox.
    # Dropbox automatically deletes the file from local storage once it is uploaded.
    while True:
        file_path = runmotiondetection_queue.get()
        print("        sending file to cloud "+file_path,flush=True)
        file_name = file_path.split('/')[-1]
        os.rename(file_path,bagfiles_dir_path_motion+file_name)

def deleteFile(deletefile_queue):
    while True:
        time.sleep(1)
        file_path = deletefile_queue.get()
        print("            deleting file "+file_path,flush=True)
        while True:
            try:
                os.remove(file_path)
                print("            file deleted: "+file_path+'\n',flush=True)
                break
            except Exception as e:
                print("            failed to delete file: "+file_path,flush=True)
                print("           ",e,flush=True)
                time.sleep(5)



def main():
    savebagfile_runmotiondetection_queue = Queue()
    runmotiondetection_sendfiletocloud_queue = Queue()
    any_deletefile_queue = Queue()

    safebagfile_process = Process(target=saveBagFile,args=(savebagfile_runmotiondetection_queue,))
    runmotiondetection_process = Process(target=runMotionDetection,args=(savebagfile_runmotiondetection_queue,runmotiondetection_sendfiletocloud_queue,any_deletefile_queue,))
    sendfiletocloud_process = Process(target=sendFileToCloud,args=(savebagfile_runmotiondetection_queue,))
    deletefile_process = Process(target=deleteFile,args=(any_deletefile_queue,))

    safebagfile_process.start()
    runmotiondetection_process.start()
    sendfiletocloud_process.start()
    deletefile_process.start()

    safebagfile_process.join()
    runmotiondetection_process.join()
    sendfiletocloud_process.join()
    deletefile_process.join()


    # bag_file_paths = []
    # bag_file_paths += ["../sample bag data/object_detection2.bag"]
    # # bag_file_paths += ["../sample bag data/outdoors.bag"]
    # bag_file_paths += ["../sample bag data/Alternating motion every 15 for 2 mins incremental motion-002.bag"]
    # bag_file_paths += ["../sample bag data/Alternating motion under bed sheets every 15 incremental 2 min-003.bag"]
    # bag_file_paths += ["../sample bag data/No Motion 30 seconds.bag"]

    # show_plot = True
    # show_plot = False
    # save_plot = True
    # save_plot = False

    # t_init = time()




    # for bag_file_path in bag_file_paths:
        
    #     t0 = time()

    #     all_frame_numbers, FNs, SDs = GetStandardDeviationsFromBag(bag_file_path, 10, 10)

    #     elapsed_time = time() - t0
    #     frames_per_sec = len(all_frame_numbers) / (elapsed_time + 0.0000001)
    #     print("\nelapsed time",elapsed_time)
    #     print("frames analyzed per second",frames_per_sec,end='\n')

    #     if save_plot or show_plot:
    #         bag_file_nickname = bag_file_path.split('/')[-1].split('\\')[-1].split('.')[0]
    #         plt.figure(1)
    #         plt.title(bag_file_nickname)
    #         plt.plot(FNs,SDs,color='blue',linewidth=1.0,label='Intel motion detection algorithm')
    #         # plt.axvline(x=71,linewidth=0.7,color='red',linestyle='--')
    #         plt.legend()
    #         if save_plot:
    #             plt.savefig('output/'+bag_file_nickname+' '+str(int(time()))+'.png')
    #         if show_plot:
    #             plt.show()
    #         else:
    #             plt.close()

    # print("total time:",time() - t_init())



if __name__ == '__main__':
    main()