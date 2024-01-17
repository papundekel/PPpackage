FROM archlinux

RUN pacman --noconfirm -Syu

RUN pacman --noconfirm -S podman

ENTRYPOINT [ "podman", "system", "service", "--time", "0" ]
