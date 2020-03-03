import numpy as np
import time
from RunMotionDetection import GetStandardDeviationsFromBag
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from RunMotionDetection import GetStandardDeviationsFromBag
from glob import glob
from pynput import keyboard
from matplotlib import pyplot as plt


'''
pip install pyrealsense2
pip install opencv-python
pip install pynput
'''


CAMERA_FRAMERATE = 30
SECONDS_PER_RECORDING = 300.0
#STANDARD_DEVIATION_THRESHOLD = 28000
NUM_POINTS_ABOVE_THRESHOLD_SOUGHT = 3
use_filters = True
bagfiles_dir_path_new = 'new_bags/'
bagfiles_dir_path_motion = 'bags_with_motion/'
save_plot = True
show_plot = False
plot_dir_path_motion = 'plots_with_motion/'
plot_dir_path_no_motion = 'plots_without_motion/'

def saveBagFile(runmotiondetection_queue,keypress_queue):
    while True:

        # First, check if user pressed key to stop recording
        try:
            # Queue.get(block=False) throws exception if nothing in queue
            message = keypress_queue.get(block=False)
            if message == 'stop':
                print('stopping recording bag files')
                return
        except:
            pass

        # Get current time to name the file
        Date = time.asctime(time.localtime(time.time())).replace(':','-')
        file_path = bagfiles_dir_path_new + str(int(time.time())) + ' ' + Date + '.bag'
        
        # Configure depth and color streams
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, CAMERA_FRAMERATE)
        config.enable_record_to_file(file_path)
        
        # Start streaming
        print("creating bag file "+file_path,flush=True)
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
                    print("saving bag file "+file_path,flush=True)
                    break
        finally:
            # Stop streaming
            pipeline.stop()
            del(pipeline)
            del(config)
            runmotiondetection_queue.put(file_path)

def on_activate_f(savebagfile_queue):
    print('f key pressed')
    savebagfile_queue.put('stop')

def keyPressMonitor(savebagfile_queue):
    # Collect events until released
    with keyboard.GlobalHotKeys({
            'f': lambda: on_activate_f(savebagfile_queue)
            }) as h:
        h.join()

def runMotionDetection(savebagfile_queue,sendfiletocloud_queue,deletefile_queue, STANDARD_DEVIATION_THRESHOLD):
    while True:
        file_path = savebagfile_queue.get()
        print("    running motion detection on "+file_path,flush=True)

        _,FNs,SDs = GetStandardDeviationsFromBag(file_path,10,10,filter=use_filters)
        
        above_thresh = SDs > STANDARD_DEVIATION_THRESHOLD
        count = sum([1 if (above_thresh[i-1] and above_thresh[i] and above_thresh[i+1]) else 0 for i in range(len(above_thresh))[1:-1]])
        if count > NUM_POINTS_ABOVE_THRESHOLD_SOUGHT:
            print("    motion detected",flush=True)
            sendfiletocloud_queue.put(file_path)
            bag_file_nickname = file_path.split('/')[-1].split('\\')[-1].split('.')[0]
            plt.figure(1)
            plt.title(bag_file_nickname)
            plt.plot(FNs,SDs,color='blue',linewidth=1.0,label='Intel motion detection algorithm')
            plt.axhline(y=STANDARD_DEVIATION_THRESHOLD)
            plt.legend()
            if save_plot:
                plt.savefig(plot_dir_path_motion + bag_file_nickname+' '+str(int(time.time()))+'.png')
                # SavePlot(path=plot_dir_path_motion + bag_file_nickname+' '+str(int(time.time()))+'.png', title=bag_file_nickname, x=FNs,y=SDs,hline=STANDARD_DEVIATION_THRESHOLD)
            if show_plot:
                plt.show()
            plt.close()
        else:
            print("    NO motion detected",flush=True)
            deletefile_queue.put(file_path)
            bag_file_nickname = file_path.split('/')[-1].split('\\')[-1].split('.')[0]
            plt.figure(1)
            plt.title(bag_file_nickname)
            plt.plot(FNs,SDs,color='blue',linewidth=1.0,label='Intel motion detection algorithm')
            plt.axhline(y=STANDARD_DEVIATION_THRESHOLD)
            plt.legend()
            if save_plot:
                plt.savefig(plot_dir_path_no_motion + bag_file_nickname+' '+str(int(time.time()))+'.png')
            if show_plot:
                plt.show()
            plt.close()

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

    # Delete all bag files that haven't been analyzed yet. This is to prevent backlogs.
    old_bag_paths = glob(bagfiles_dir_path_new+"*.bag")
    for obp in old_bag_paths:
        os.remove(obp)
    print(len(old_bag_paths),'old bag files deleted')
    calibration_path = 'new_bags/' + 'Calibration' + '.bag'
    
    time.sleep(10)
    print("beginning calibration",flush=True)

    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, CAMERA_FRAMERATE)
    config.enable_record_to_file(calibration_path)
    
    # Start streaming
    print("creating calibration bag file "+calibration_path,flush=True)
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
            if (time.time() - t0) >= 60.0:
                print("saving calibration bag file "+calibration_path,flush=True)
                break
    finally:
        # Stop streaming
        pipeline.stop()
        del(pipeline)
        del(config)
    #Get Standard Deviations for calibration
    print("Calculating SDs for calibration")
    _,FNs,SDs = GetStandardDeviationsFromBag(calibration_path,10,10,filter=use_filters)
    print("SDs calculated for calibration")
    big = np.partition(np.array(SDs), -3)[-3]
    STANDARD_DEVIATION_THRESHOLD = big
    print("Threshold for calibration is " + str(STANDARD_DEVIATION_THRESHOLD))
    bag_file_nickname = 'Calibration SDs'
    plt.figure(1)
    plt.title(bag_file_nickname)
    plt.plot(FNs,SDs,color='blue',linewidth=1.0,label='Intel motion detection algorithm')
    plt.axhline(y=STANDARD_DEVIATION_THRESHOLD)
    plt.legend()
    if save_plot:
        plt.savefig(plot_dir_path_no_motion+bag_file_nickname+'.png')
    if show_plot:
        plt.show()
    plt.close()

    

    # initialize multiprocessing queues
    savebagfile_runmotiondetection_queue = Queue()
    runmotiondetection_sendfiletocloud_queue = Queue()
    any_deletefile_queue = Queue()
    key_savebagfile_queue = Queue()

    # declare multiprocessing processes, and connect with queues
    savebagfile_process = Process(target=saveBagFile,args=(savebagfile_runmotiondetection_queue,key_savebagfile_queue,))
    runmotiondetection_process = Process(target=runMotionDetection,args=(savebagfile_runmotiondetection_queue,runmotiondetection_sendfiletocloud_queue,any_deletefile_queue,STANDARD_DEVIATION_THRESHOLD,))
    sendfiletocloud_process = Process(target=sendFileToCloud,args=(runmotiondetection_sendfiletocloud_queue,))
    deletefile_process = Process(target=deleteFile,args=(any_deletefile_queue,))
    key_process = Process(target=keyPressMonitor,args=(key_savebagfile_queue,))

    # start multiprocessing processes
    savebagfile_process.start()
    runmotiondetection_process.start()
    sendfiletocloud_process.start()
    deletefile_process.start()
    key_process.start()

    # end multiprocessing processes if they finish
    # they won't finish (barring exceptions), since they're all infinite while loops.
    savebagfile_process.join()
    runmotiondetection_process.join()
    sendfiletocloud_process.join()
    deletefile_process.join()
    key_process.join()


if __name__ == '__main__':
    main()