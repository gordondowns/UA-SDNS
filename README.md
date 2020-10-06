# UA-SDNS

Seizure detection and notification system utilizing Python 3 and Intel's RealSense D415 depth camera

Initially developed at the University of Arizona with funding from Intel Corporation

## Installation

UA-SDNS requires [Python 3](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads) to install. Windows 10 is currently the only operating system supported.

1. Download this repository:
   ```sh
   $ git clone https://github.com/gordondowns/UA-SDNS.git
   ```

2. Install dependencies and create the virtual environment by running `UA-SDNS\install.bat`.

   Using the commandline:
   ```sh
   $ cd UA-SDNS
   $ install.bat
   ```
   Or run `UA-SDNS\install.bat` using the File Explorer.

3. To make the SDNS program start on startup, make a shortcut to `UA-SDNS\data_collection2\sdns.bat` and put it in `C:\Users\username\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`.

## Usage

Run `UA-SDNS\data_collection2\sdns.bat` to start the program.

Then, control the system by pressing keys on your keyboard. Note that you do not have to have the sdns.bat window active in order to enter commands.
  
| key | action |
|--|--|
| spacebar / s | save last 5 minutes of video |
| q | quit and delete the recordings |
| p | pause recording |
| r | resume paused recording |

## Troubleshooting tips

| Error Message | Solution |
|--|--|
| `Frame did not arrive within 1000` | RealSense D415 camera connection failed. Unplug the camera, plug it back in, and re-run sdns.bat. |
| `MemoryError: Unable to allocate XX.X GiB for an array with shape (XXX, XXX, XXX) and data type uintX` | Computer memory is insufficient to store a video of the length and resolution described in `data_collection2\main.py`. Please go to `data_collection2\main.py` and modify the parameter `SECONDS_PER_RECORDING`. |
| `RuntimeError: Couldn't resolve requests` | Depth resolution is too high for your hardware setup. First, try plugging the RealSense D415 camera into a USB 3 port (the Intel RealSense Viewer can tell you what kind of USB port the camera is plugged into). If that doesn't work, try using a lower depth resolution by modifying the parameters `DEPTH_X_SIZE,DEPTH_Y_SIZE` in the file `data_collection2\main.py`. |

Have a problem you can't figure out? Contact gordon.sdns@gmail.com for technical assistance.  

## I want to contribute!

That's awesome!

If you'd like to **contribute data and use the system as we develop it**, contact Iwan (email TBD).

If you are a developer and would like to **contribute to the codebase**, contact Gordon at gordon.sdns@gmail.com.  

## License

GNU General Public License v3.0