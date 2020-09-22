# UA-SDNS
Seizure detection and notification system utilizing Python and Intel's RealSense D415 depth camera

Initially developed at the University of Arizona with funding from Intel Corporation

### Installation

UA-SDNS requires [Python 3](https://www.python.org/downloads/) to install.

After installing Python 3, install pipenv:
```sh
$ pip install pipenv
```

Download this repository:
```sh
$ git clone https://github.com/gordondowns/UA-SDNS.git
```

Install dependencies:
```sh
$ cd UA-SDNS
$ pipenv install --dev
```

For production environments, omit ```--dev```:
```sh
$ pipenv install
```

License
----

GNU General Public License v3.0