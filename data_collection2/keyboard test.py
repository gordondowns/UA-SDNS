from pynput import keyboard
import time

break_program = False
def on_press(key):
    global break_program
    print (key)
    if key == keyboard.Key.end:
        print ('end pressed')
        break_program = True
        return False

def on_activate_f(j):
    global break_program
    print('f key pressed')
    break_program = True
    # dothething_queue.put('save')
    return False


# with keyboard.Listener(on_press=on_press) as listener:
with keyboard.Listener(on_press=lambda key: on_activate_f(key)) as listener:
# with keyboard.GlobalHotKeys({
#         # keyboard.Key.space: lambda: on_activate_space(dothething_queue),
#         'f': lambda: on_activate_f(),
#         }) as listener:

    while break_program == False:
        print ('program running')
        time.sleep(2)
    listener.join()