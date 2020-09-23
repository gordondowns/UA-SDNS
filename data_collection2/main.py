import numpy as np
import time
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from pynput import keyboard, Key


CAMERA_FRAMERATE = 30
SECONDS_PER_RECORDING = 20 * 60
bagfiles_dir_path_new = 'recordings/'

def DoTheThing(keypress_queue):
    matrix_length = int(SECONDS_PER_RECORDING*CAMERA_FRAMERATE)
    infrared_matrix = np.zeros((matrix_length,640,480),dtype=np.int16)
    depth_matrix = np.zeros((matrix_length,1280,720),dtype=np.int16)

    # Get current time to save in the info.txt file
    start_time = time.asctime(time.localtime(time.time())).replace(':','-')
    
    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, CAMERA_FRAMERATE)
    config.enable_stream(rs.stream.infrared, 640, 480, rs.format.y8, CAMERA_FRAMERATE)
    # config.enable_record_to_file(file_path)

    # Start streaming
    pipeline.start(config)
    i = 0

    while True:

        # First, check if user pressed key to stop recording
        try:
            # Queue.get(block=False) throws exception if nothing in queue
            message = keypress_queue.get(block=False)
            if message == 'save':
                print('stopping recording and saving to disk...')

                # Stop streaming
                pipeline.stop()
                del(pipeline)
                del(config)

                # save recording to disk
                end_time = time.asctime(time.localtime(time.time())).replace(':','-')
                newdir = 'recordings/'+end_time+'/'
                os.mkdir(newdir)
                np.roll(infrared_matrix,shift=i,axis=0)
                np.roll(depth_matrix,shift=i,axis=0)
                np.save(newdir+'depth_matrix.npy',depth_matrix)
                np.save(newdir+'infrared_matrix.npy',infrared_matrix)
                with open(newdir+'info.txt','w') as f:
                    f.write('time that recording system was initialized: '+start_time+'\ntime that "save" button was pressed: '+end_time)
                print('recordings saved to "'+newdir+'"')
                return
        except:
            pass
        
        try:
            # Wait for a coherent pair of frames: depth and infrared
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            infrared_frame = frames.get_infrared_frame()
            if not depth_frame or not infrared_frame:
                continue
            depth_image = np.asanyarray(depth_frame.get_data())
            infrared_image = np.asanyarray(infrared_frame.get_data())

            depth_matrix[i] = depth_image
            infrared_matrix[i] = infrared_image
            i += 1
            
        except:
            pass


def on_activate_space(dothething_queue):
    print('spacebar pressed')
    dothething_queue.put('save')

def keyPressMonitor(dothething_queue):
    # Collect events until released
    with keyboard.GlobalHotKeys({
            Key.space: lambda: on_activate_space(dothething_queue),
            # 'f': lambda: on_activate_f(dothething_queue),
            }) as h:
        h.join()

def main():

    # initialize multiprocessing queues
    keypress_queue = Queue()

    # declare multiprocessing processes, and connect with queues
    dothething_process = Process(target=DoTheThing,args=(keypress_queue,))
    key_process = Process(target=keyPressMonitor,args=(keypress_queue,))

    # start multiprocessing processes
    dothething_process.start()
    key_process.start()

    # end multiprocessing processes once they finish
    dothething_process.join()
    key_process.join()


if __name__ == '__main__':
    main()