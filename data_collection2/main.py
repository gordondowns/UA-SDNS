import numpy as np
import time
from multiprocessing import Process, Pipe, Queue, SimpleQueue
import os
import pyrealsense2 as rs
from pynput import keyboard
import imageio
import pyttsx3


CAMERA_FRAMERATE = 30
SECONDS_PER_RECORDING = 5 * 60
RECORDING_DIR = 'recordings/'
DEPTH_X_SIZE,DEPTH_Y_SIZE = 1280,720
# DEPTH_X_SIZE,DEPTH_Y_SIZE = 960,540
# DEPTH_X_SIZE,DEPTH_Y_SIZE = 640,480
INFRARED_X_SIZE,INFRARED_Y_SIZE = 640,480
SAVE_INFRARED_NPY = False
ENABLE_TEXT_TO_SPEECH = True


#################################################################
#    User should not have to modify anything below this line    #
#################################################################


def RecordRollingVideo(keypress_queue):
    # calculate size of depth and IR matrices
    matrix_length = int(SECONDS_PER_RECORDING*CAMERA_FRAMERATE)

    # initialize states
    i = 0
    state = 'initialize'
    pipeline_on = False
    matrices_allocated = False

    while True:
        # First, check if user pressed a key to change states
        try:
            # Queue.get(block=False) throws exception if nothing in queue
            state = keypress_queue.get(block=False)
        except:
            pass # state variable unchanged
        
        if state == 'initialize':
            print('initializing SDNS program')
            # allocate memory for depth and IR matrices
            depth_matrix = np.zeros((matrix_length,DEPTH_Y_SIZE,DEPTH_X_SIZE),dtype=np.uint16)
            infrared_matrix = np.zeros((matrix_length,INFRARED_Y_SIZE,INFRARED_X_SIZE),dtype=np.uint8)
            matrices_allocated = True
            # Get current time to save in the info.txt file
            start_time = time.asctime(time.localtime(time.time())).replace(':','-')
            state = 'resume'
        elif state == 'resume':
            if not matrices_allocated:
                state = 'initialize'
                continue
            if pipeline_on:
                print('WARNING: System is already recording. No action taken.')
                state = 'record'
            else:
                # Configure depth and IR streams
                pipeline = rs.pipeline()
                config = rs.config()
                config.enable_stream(rs.stream.depth, DEPTH_X_SIZE,DEPTH_Y_SIZE, rs.format.z16, CAMERA_FRAMERATE)
                config.enable_stream(rs.stream.infrared, INFRARED_X_SIZE,INFRARED_Y_SIZE, rs.format.y8, CAMERA_FRAMERATE)

                # Start streaming
                pipeline.start(config)
                pipeline_on = True
                print('starting recording')
                print('press:      to:')
                print('spacebar    save last',SECONDS_PER_RECORDING,'seconds of video')
                print('q           quit and delete the recordings')
                print('p           pause recording')
                print('r           resume recording')
                state = 'record'
        elif state == 'pause':
            if pipeline_on:
                pipeline.stop()
                pipeline_on = False
                print('recording paused')
                state = 'wait'
            else:
                print('WARNING: System is already paused. No action taken.')
                state = 'wait'
        elif state == 'wait':
            time.sleep(0.5)
        elif state == 'save':
            print('saving recordings')
            if pipeline_on:
                print('stopping recording')
                pipeline.stop()
                pipeline_on = False
            else:
                print('WARNING: System was not recording, so saved video may not be very recent.')
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
            imageio.mimwrite(newdir+'infrared_video.mp4', infrared_matrix, fps=30)
            del(infrared_matrix)
            matrices_allocated = False

            # save info.txt
            with open(newdir+'info.txt','w') as f:
                f.write(f'time that recording system was initialized: {start_time}\ntime that "save" button was pressed: {end_time}')
            print('recordings saved to "'+newdir+'"')
            print('')
            state = 'initialize'
        elif state == 'quit':
            if pipeline_on:
                print('stopping recording')
                pipeline.stop()
            try:
                del(pipeline)
                del(config)
            except:
                pass

            print('deleting recordings')
            try:
                del(depth_matrix)
                del(infrared_matrix)
            except:
                pass
            matrices_allocated = False
            print('recordings deleted')
            return
        elif state == 'record':
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
                i += 1
                if i == matrix_length:
                    i = 0
                # del(frames)
                # del(depth_frame)
                # del(infrared_frame)
            except Exception as e:
                print('Exception while trying to collect frames:',e)
                pass


def on_keypress(key,keypress_queue):
    if ENABLE_TEXT_TO_SPEECH:
        engine = pyttsx3.init()
        
    if key == keyboard.Key.space:
        print('spacebar pressed')
        keypress_queue.put('save')
        if ENABLE_TEXT_TO_SPEECH:
            engine.say('save')
            engine.runAndWait()
    elif hasattr(key,'char'): #letters
        if key.char == 'q':
            print('q key pressed')
            keypress_queue.put('quit')
            if ENABLE_TEXT_TO_SPEECH:
                engine.say('quit')
                engine.runAndWait()
            return False
        elif key.char == 's':
            print('s key pressed')
            keypress_queue.put('save')
            if ENABLE_TEXT_TO_SPEECH:
                engine.say('save')
                engine.runAndWait()
        elif key.char == 'p':
            print('p key pressed')
            keypress_queue.put('pause')
            if ENABLE_TEXT_TO_SPEECH:
                engine.say('pause')
                engine.runAndWait()
        elif key.char == 'r':
            print('r key pressed')
            keypress_queue.put('resume')
            if ENABLE_TEXT_TO_SPEECH:
                engine.say('re zoom')
                engine.runAndWait()


def keyPressMonitor(keypress_queue):
    with keyboard.Listener(on_press=lambda key: on_keypress(key,keypress_queue)) as listener:
        listener.join()

def main():
    print(f'configuration: Depth resolution: {DEPTH_X_SIZE}x{DEPTH_Y_SIZE}. Seconds per recording: {SECONDS_PER_RECORDING}')

    # initialize multiprocessing queues
    keypress_queue = Queue()

    # declare multiprocessing processes, and connect with queues
    recordrollingvideo_process = Process(target=RecordRollingVideo,args=(keypress_queue,))
    key_process = Process(target=keyPressMonitor,args=(keypress_queue,))

    # start multiprocessing processes
    recordrollingvideo_process.start()
    key_process.start()

    # end multiprocessing processes once they finish
    recordrollingvideo_process.join()
    key_process.join()


if __name__ == '__main__':
    main()