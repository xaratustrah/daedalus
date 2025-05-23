# daedalus - An integrated control system for internal multiphase targets for heavy ion storage rings

<div style="margin-left:auto;margin-right:auto;text-align:center">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/daedalus.jpg" width="256">
</div>

*daedalus* is an integrated control system for internal multiphase targets for heavy ion storage rings.


Here are some pics:
<div style="margin-left:auto;margin-right:auto;text-align:center">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/dae_top.jpg" width="512">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/dae_bot.jpg" width="512">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/dae_front.jpg" width="512">
<img src="https://raw.githubusercontent.com/xaratustrah/daedalus/master/rsrc/dae_back.jpg" width="512">
</div>

## Installation
Please download the latest version of [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/). Newest versions require setting up username / password already in the imager tool. You can also enable SSH from there. Then you can expand file system using the script `raspi-config`. Then you need a couple of things:

```bash
sudo apt udpate
sudo apt -y install git python3-pip
```

The clone the repository and go inside that directory and type (you may need to provide the command line arg `--break-system-packages` before the `-r` and before `.` below, depending on your system, and how you are using your Raspberry Pi. Please use with care!):

First you need to install `voreas` library:

```bash
cd git
git clone https://github.com/ShaynaNepaul/voreas
cd voreas
pip3 install -r requirements.txt
pip install .

```

You can check whether the `voreas` library has been installed correctly, you can do:

```bash
python3 -c 'from voreas.tools import get_density_value;print(get_density_value(name = "H2", T = 40, p = 10, S1 = 2, S2 = 2, S3 = 5, S4 = 4))'
```
you will receive some number without error or crash.


Now the installation of `daedalus` itself:

```bash
cd git
git clone https://github.com/xaratustrah/daedalus
cd daedalus
pip3 install -r requirements.txt
pip3 install .
```

For uninstalling both you can type:

```bash
pip3 uninstall daedalus
pip3 uninstall voreas
```


## Usage

It is recommended to start each program part on a different screen session:

```bash
cd git/daedalus
screen -DRS daedalus
```

then create 3 different screens, and run each of these commands there.

```bash
python3 -m daedalus_mcu --debug --cfg daedalus_mcu_cfg_defaults.toml
python3 -m daedalus_tcu --debug --cfg daedalus_tcu_cfg_cryring.toml
python3 -m daedalus_grf --debug --cfg daedalus_grf_cfg_cryring.toml
```



## Licensing

Please see the file [LICENSE.md](./LICENSE.md) for further information about how the content is licensed.

## Acknowledgements

This code has been inspired by a previous work by Ulrich Popp available on [https://codeberg.org/HoSnoopy/TB6600-RPI](https://codeberg.org/HoSnoopy/TB6600-RPI).
