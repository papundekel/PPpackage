FROM greyltc/archlinux-aur:paru

RUN mkdir -p /workdir

RUN pacman --noconfirm -Syu pacutils pacman-contrib python

RUN aur-install conan

RUN pacman --noconfirm -S fakeroot fakechroot

RUN pacman --noconfirm -S yajl

RUN pacman --noconfirm -S cmake

RUN pacman --noconfirm -Syu python-typer

RUN pacman --noconfirm -Syu meson

RUN pacman --noconfirm -Syu runc

WORKDIR /workdir

COPY --chown=ab:ab ./libalpm-pp /workdir/libalpm-pp 

RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

COPY fakealpm/ /workdir/fakealpm
COPY --chmod=a+x ./build_fakealpm.sh /workdir/

RUN ./build_fakealpm.sh

COPY *.jinja profile /workdir/

COPY --chmod=a+x *.py manager.sh /workdir/

RUN systemd-machine-id-setup
