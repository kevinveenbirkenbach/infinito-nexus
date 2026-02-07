# Virtual Box

```bash
	sudo pacman -S virtualbox "$(pacman -Qsq "^linux" | grep "^linux[0-9]*[-rt]*$" | awk '{print $1"-virtualbox-host-modules"}' ORS=' ')" &&
	sudo vboxreload &&
	pamac build virtualbox-ext-oracle &&
	sudo gpasswd -a "$USER" vboxusers || exit 1
	echo "Keep in mind to install the guest additions in the virtualized system. See https://wiki.manjaro.org/index.php?title=VirtualBox"
```