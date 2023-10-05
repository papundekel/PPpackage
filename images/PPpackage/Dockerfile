FROM greyltc/archlinux-aur:paru

RUN mkdir -p /workdir
WORKDIR /workdir

RUN pacman --noconfirm -Syu

RUN systemd-machine-id-setup

RUN pacman --noconfirm -S pacutils
RUN pacman --noconfirm -S pacman-contrib
RUN pacman --noconfirm -S python
RUN pacman --noconfirm -S fakeroot
RUN pacman --noconfirm -S fakechroot
RUN pacman --noconfirm -S yajl
RUN pacman --noconfirm -S cmake
RUN pacman --noconfirm -S python-typer
RUN pacman --noconfirm -S meson
RUN aur-install conan

COPY --chown=ab:ab ./libalpm-pp /workdir/libalpm-pp 
RUN cd libalpm-pp/ && ./PKGBUILD.sh < PKGBUILD.template > PKGBUILD && sudo --user ab makepkg --skippgpcheck --install --noconfirm

COPY fakealpm/ /workdir/fakealpm
COPY --chmod=a+x ./build_fakealpm.sh /workdir/
RUN ./build_fakealpm.sh

COPY profile.jinja conanfile-fetch.py.jinja conanfile-leaf.py.jinja conanfile-root.py.jinja profile /workdir/
COPY --chmod=a+x PPpackage_utils.py PPpackage.py PPpackage_sub.py PPpackage_arch.py PPpackage_conan.py PPpackage_conan_deployer.py manager.sh /workdir/
