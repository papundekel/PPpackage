FROM greyltc/archlinux-aur:paru

RUN mkdir -p /workdir

RUN pacman --noconfirm -Syu pacutils pacman-contrib python

RUN aur-install bindfs conan

RUN pacman --noconfirm -S fakeroot fakechroot

RUN pacman --noconfirm -S yajl

RUN pacman --noconfirm -S cmake

COPY ./ /workdir

WORKDIR /workdir
