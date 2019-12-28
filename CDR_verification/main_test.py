import numpy as np
import time
from matplotlib import pyplot as plt
from RunMotionDetection import GetStandardDeviationsFromBag
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from RunMotionDetection import GetStandardDeviationsFromBag as motiondetection1
from RunMotionDetection2 import GetStandardDeviationsFromBag as motiondetection2

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
plot_dir_path = 'plots/'
save_plot = True
show_plot = False
save_only_one_bag = False

def saveBagFile(runmotiondetection_queue):
    while True:
        #Get current time to name the file
        Date = time.asctime(time.localtime(time.time())).replace(':','-')
        file_path = bagfiles_dir_path_new + str(int(time.time())) + ' ' + Date + '.bag'
        
        # Configure depth and color streams
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, CAMERA_FRAMERATE)
        config.enable_record_to_file(file_path)
        
        # Start streaming
        print("creating bag file to "+file_path,flush=True)
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

            if save_only_one_bag:
                # break to save only one snippet
                break

def runMotionDetection(savebagfile_queue,sendfiletocloud_queue,deletefile_queue):
    while True:
        file_path = savebagfile_queue.get()
        print("    running motion detection on "+file_path,flush=True)

        all_frame_numbers,all_depth_images,all_color_images,FNs,SDs,recording_time_length = motiondetection2(file_path,10,10)
        num_frames = all_frame_numbers[-1] - all_frame_numbers[0] + 1

        # convert from milliseconds to seconds
        time_length = recording_time_length / 1000

        print("    "+"number of frames".ljust(30),num_frames)
        print("    "+"time elapsed".ljust(30),time_length)
        
        print("    "+"true framerate".ljust(30),num_frames/time_length)
        print("    "+"depth image resolution".ljust(30),all_depth_images[0].shape[0],'x',all_depth_images[0].shape[1])
        print("    "+"color image resolution".ljust(30),all_color_images[0].shape[0],'x',all_color_images[0].shape[1])


        bag_file_nickname = file_path.split('/')[-1].split('\\')[-1].split('.')[0]
        plt.figure(1)
        plt.title(bag_file_nickname)
        plt.plot(FNs,SDs,color='blue',linewidth=1.0,label='Intel motion detection algorithm')
        plt.axhline(y=STANDARD_DEVIATION_THRESHOLD)
        plt.legend()
        if save_plot:
            plt.savefig(plot_dir_path+bag_file_nickname+' '+str(int(time.time()))+'.png')
        if show_plot:
            plt.show()
        plt.close()


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
        time.sleep(1)
        file_path = runmotiondetection_queue.get()
        print("        sending file to cloud "+file_path,flush=True)
        file_name = file_path.split('/')[-1]
        while True:
            try:
                os.rename(file_path,bagfiles_dir_path_motion+file_name)
                print("            file sent to cloud: "+file_path,flush=True)
                break
            except Exception as e:
                print("            failed to send file to cloud: "+file_path,flush=True)
                print("           ",e,flush=True)
                time.sleep(5)

def deleteFile(deletefile_queue):
    while True:
        time.sleep(1)
        file_path = deletefile_queue.get()
        print("            deleting file "+file_path,flush=True)
        while True:
            try:
                os.remove(file_path)
                print("            file deleted: "+file_path,flush=True)
                break
            except Exception as e:
                print("            failed to delete file: "+file_path,flush=True)
                print("           ",e,flush=True)
                time.sleep(5)



def main():
    savebagfile_runmotiondetection_queue = Queue()
    runmotiondetection_sendfiletocloud_queue = Queue()
    any_deletefile_queue = Queue()

    savebagfile_process = Process(target=saveBagFile,args=(savebagfile_runmotiondetection_queue,))
    runmotiondetection_process = Process(target=runMotionDetection,args=(savebagfile_runmotiondetection_queue,runmotiondetection_sendfiletocloud_queue,any_deletefile_queue,))
    sendfiletocloud_process = Process(target=sendFileToCloud,args=(runmotiondetection_sendfiletocloud_queue,))
    deletefile_process = Process(target=deleteFile,args=(any_deletefile_queue,))

    savebagfile_process.start()
    runmotiondetection_process.start()
    sendfiletocloud_process.start()
    deletefile_process.start()

    savebagfile_process.join()
    runmotiondetection_process.join()
    sendfiletocloud_process.join()
    deletefile_process.join()


if __name__ == '__main__':
    main()