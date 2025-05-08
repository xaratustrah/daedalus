# daedalus - Stepper motor controller for internal multiphase target

<div style="margin-left:auto;margin-right:auto;text-align:center">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/daedalus.jpg" width="512">
</div>

*daedalus* is an integrated control system for internal multiphase targets for heavy ion storage rings.

## Installation
Please download the latest version of [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/). Newest versions require setting up username / password already in the imager tool. You can also enable SSH from there. Then you can expand file system using the script `raspi-config`. Then you need a couple of things:

```
sudo apt udpate
sudo apt -y install git python3-pip
```

The clone the repository and go inside that directory and type (you may need to provide the command line arg `--break-system-packages` before the `-r` and before `.` below, depending on your system, and how you are using your Raspberry Pi. Please use with care!):

```
pip install -r requirements.txt
pip3 install .
```

For uninstalling you can type:

```
pip3 uninstall daedalus
```


## Usage

TBD

## Licensing

Please see the file [LICENSE.md](./LICENSE.md) for further information about how the content is licensed.

## Acknowledgements

This code is based on a previous work by Ulrich Popp [HoSnoopy@GitHUB](https://codeberg.org/HoSnoopy). The MCU part is inspired by the code available on [https://codeberg.org/HoSnoopy/TB6600-RPI](https://codeberg.org/HoSnoopy/TB6600-RPI).
