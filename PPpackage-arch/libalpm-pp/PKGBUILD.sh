#!/usr/bin/env sh

PKGVER=$(pacman -Q pacman | cut -d " " -f 2 | rev | cut -d "-" -f 2- | rev)

sed "s|PKGVER|$PKGVER|"
