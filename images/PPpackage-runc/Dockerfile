FROM greyltc/archlinux-aur:paru

RUN mkdir --parents /workdir
WORKDIR /workdir

RUN pacman --noconfirm --sync --refresh --sysupgrade

RUN pacman --noconfirm --sync python
RUN pacman --noconfirm --sync python-typer
RUN pacman --noconfirm --sync runc
RUN pacman --noconfirm --sync python-daemon

COPY --chmod=a+x PPpackage_utils.py PPpackage_runc.py /workdir/
RUN mkdir --parents --mode 777 /workdir/PPpackage-runc

ENTRYPOINT ["./PPpackage_runc.py", "PPpackage-runc/"]
