FROM greyltc/archlinux-aur:paru-20231001.0.289

RUN mkdir --parents /workdir
WORKDIR /workdir

RUN pacman --noconfirm --sync --refresh --sysupgrade

RUN pacman --noconfirm --sync python
RUN pacman --noconfirm --sync runc

ENV VIRTUAL_ENV=/workdir/.venv/
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY PPpackage-utils/ /workdir/packages/PPpackage-utils/
RUN pip install packages/PPpackage-utils/

COPY PPpackage-runc/ /workdir/packages/PPpackage-runc/
RUN pip install packages/PPpackage-runc/

RUN mkdir --parents --mode 777 /workdir/PPpackage-runc
