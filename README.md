# daedalus - Stepper motor controller for internal multiphase target

<div style="margin-left:auto;margin-right:auto;text-align:center">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/daedalus.jpg" width="512">
</div>

*daedalus* is an easy to use stepper motor controller for Raspberry Pi. 

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


#### Logger

A logger file name can be provided in order to put actions and readout information together with a time stamp in a log file. You activate the logger by using the `--log` swtich:

```
daedalus --log ./logfile
```

#### Motor speed

The switch `--speed` is for setting the rotation speed.

```
daedalus --speed 1000 --log ./logfile
```

#### Calibration file
Working with a calibration file insures a safer operation. In the calibration file, which is [TOML format]() limits can be set for every motor. You can provide the name of the calibration file as a command line argument:

```
daedalus --speed 1000 --log ./logfile --cal clibration.toml
```

This works for all modes of operation. Here is the structure of the calibration file:

```toml
# Value entry for every motor

[mot0]

# Absolute minimum and maximum in mm
limit_outside = 40
limit_inside = 60

# Provide two calibration points
# For calibration points, within each pair, please use either floats or ints, do not mix.
# First value is in mm, second the ADC / poti value
cal_points = [[49, 1864], [83, 1072]]
```

## Hardware description

TBD

## Licensing

Please see the file [LICENSE.md](./LICENSE.md) for further information about how the content is licensed.

## Acknowledgements

This code is based on a previous work by Ulrich Popp [HoSnoopy@GitHUB](https://github.com/HoSnoopy).
