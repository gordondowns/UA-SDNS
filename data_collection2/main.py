import numpy as np
import time
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from pynput import keyboard
import imageio


CAMERA_FRAMERATE = 30
SECONDS_PER_RECORDING = 5 * 60
RECORDING_DIR = 'recordings/'
# DEPTH_X_SIZE,DEPTH_Y_SIZE = 1280,720
# DEPTH_X_SIZE,DEPTH_Y_SIZE = 960,540
DEPTH_X_SIZE,DEPTH_Y_SIZE = 640,480
INFRARED_X_SIZE,INFRARED_Y_SIZE = 640,480
SAVE_INFRARED_NPY = False

def RecordRollingVideo(keypress_queue):
    matrix_length = int(SECONDS_PER_RECORDING*CAMERA_FRAMERATE)
    depth_matrix = np.zeros((matrix_length,DEPTH_Y_SIZE,DEPTH_X_SIZE),dtype=np.uint16)
    infrared_matrix = np.zeros((matrix_length,INFRARED_Y_SIZE,INFRARED_X_SIZE),dtype=np.uint8)

    # Get current time to save in the info.txt file
    start_time = time.asctime(time.localtime(time.time())).replace(':','-')

    # Configure depth and color streams
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, DEPTH_X_SIZE,DEPTH_Y_SIZE, rs.format.z16, CAMERA_FRAMERATE)
    config.enable_stream(rs.stream.infrared, INFRARED_X_SIZE,INFRARED_Y_SIZE, rs.format.y8, CAMERA_FRAMERATE)

    # Start streaming
    pipeline.start(config)
    i = 0
    message = 'r'
    print('starting recording')

    while True:

        # First, check if user pressed key to stop recording
        try:
            # Queue.get(block=False) throws exception if nothing in queue
            message = keypress_queue.get(block=False)
        except:
            pass
        if message == 'save':
            print('stopping recording')
            pipeline.stop()
            del(pipeline)
            del(config)

            # save recording to disk
            end_time = time.asctime(time.localtime(time.time())).replace(':','-')
            newdir = RECORDING_DIR+end_time+'/'
            os.mkdir(newdir)
            print('rolling videos')
            infrared_matrix = np.roll(infrared_matrix,shift=-i,axis=0)
            depth_matrix = np.roll(depth_matrix,shift=-i,axis=0)
            print('saving depth video as .NPY (this step might take a minute)')
            np.save(newdir+'depth_matrix.npy',depth_matrix)
            del(depth_matrix)
            if SAVE_INFRARED_NPY:
                np.save(newdir+'infrared_matrix.npy',infrared_matrix)

            print('saving infrared video as .MP4')
            # depth_matrix = depth_matrix.astype('uint8')
            # imageio.mimwrite(newdir+'depth_video.mp4', depth_matrix, fps=30)
            imageio.mimwrite(newdir+'infrared_video.mp4', infrared_matrix, fps=30)
            del(infrared_matrix)

            # save info.txt
            with open(newdir+'info.txt','w') as f:
                f.write(f'time that recording system was initialized: {start_time}\ntime that "save" button was pressed: {end_time}')
            print('recordings saved to "'+newdir+'"')
            return
        elif message == 'quit':
            print('stopping recording')
            pipeline.stop()
            del(pipeline)
            del(config)

            print('deleting recordings')
            del(depth_matrix)
            del(infrared_matrix)
            print('recordings deleted')
            return

        # no "stop" nor "quit" keypress, so wait for frames
        try:
            # Wait for a coherent pair of frames: depth and infrared
            frames = pipeline.wait_for_frames(timeout_ms=1000)
            depth_frame = frames.get_depth_frame()
            infrared_frame = frames.get_infrared_frame()
            if not depth_frame or not infrared_frame:
                print('no frame')
                continue
            depth_image = np.asanyarray(depth_frame.get_data())
            infrared_image = np.asanyarray(infrared_frame.get_data())

            depth_matrix[i] = depth_image
            infrared_matrix[i] = infrared_image
            # print(i,end=' ')
            i += 1
            if i == matrix_length:
                i = 0
            # del(frames)
            # del(depth_frame)
            # del(infrared_frame)

        except Exception as e:
            print(e)
            pass


def on_keypress(key,dothething_queue):
    if key == keyboard.Key.space:
        print('spacebar pressed')
        dothething_queue.put('save')
        return False
    elif hasattr(key,'char'): #letters
        if key.char == 'q':
            print('q key pressed')
            dothething_queue.put('quit')
            return False

def keyPressMonitor(dothething_queue):
    with keyboard.Listener(on_press=lambda key: on_keypress(key,dothething_queue)) as listener:
        listener.join()

def main():
    print('initializing SDNS program')

    # initialize multiprocessing queues
    keypress_queue = Queue()

    # declare multiprocessing processes, and connect with queues
    dothething_process = Process(target=RecordRollingVideo,args=(keypress_queue,))
    key_process = Process(target=keyPressMonitor,args=(keypress_queue,))

    # start multiprocessing processes
    dothething_process.start()
    key_process.start()

    # end multiprocessing processes once they finish
    dothething_process.join()
    key_process.join()


if __name__ == '__main__':
    main()