FROM archlinux:latest

# 1) Pakete inkl. docker (damit docker CLI im Container vorhanden ist)
RUN pacman -Syu --noconfirm \
      base-devel \
      git \
      python \
      python-pip \
      python-setuptools \
      alsa-lib \
      go \
      rsync \
      docker \
    && pacman -Scc --noconfirm

# 2) systemctl & yay stubben
RUN printf '#!/bin/sh\nexit 0\n' > /usr/bin/systemctl \
    && chmod +x /usr/bin/systemctl \
    && printf '#!/bin/sh\nexit 0\n' > /usr/bin/yay \
    && chmod +x /usr/bin/yay

# 3) python-simpleaudio aus AUR
RUN useradd -m aur_builder \
 && su aur_builder -c "git clone https://aur.archlinux.org/python-simpleaudio.git /home/aur_builder/psa && \
                    cd /home/aur_builder/psa && \
                    makepkg --noconfirm --skippgpcheck" \
 && pacman -U --noconfirm /home/aur_builder/psa/*.pkg.tar.zst \
 && rm -rf /home/aur_builder/psa

# 4) pkgmgr + venv
ENV PKGMGR_REPO=/opt/package-manager \
    PKGMGR_VENV=/root/.venvs/pkgmgr

RUN git clone https://github.com/kevinveenbirkenbach/package-manager.git $PKGMGR_REPO \
 && python -m venv $PKGMGR_VENV \
 && $PKGMGR_VENV/bin/pip install --upgrade pip \
 && $PKGMGR_VENV/bin/pip install --no-cache-dir -r $PKGMGR_REPO/requirements.txt ansible \
 && printf '#!/bin/sh\n. %s/bin/activate\nexec python %s/main.py "$@"\n' \
           "$PKGMGR_VENV" "$PKGMGR_REPO" > /usr/local/bin/pkgmgr \
 && chmod +x /usr/local/bin/pkgmgr

ENV PATH="$PKGMGR_VENV/bin:/root/.local/bin:${PATH}"

# 6) Infinito.Nexus Quelle rein
COPY . /opt/infinito-src

# 7) Infinito via pkgmgr (shallow)
RUN pkgmgr install infinito --clone-mode shallow

# 8) Override mit lokaler Quelle
RUN INFINITO_PATH=$(pkgmgr path infinito) && \
    rm -rf "$INFINITO_PATH"/* && \
    rsync -a --delete --exclude='.git' /opt/infinito-src/ "$INFINITO_PATH"/

# 9) Symlink
RUN INFINITO_PATH=$(pkgmgr path infinito) && \
    ln -sf "$INFINITO_PATH"/main.py /usr/local/bin/infinito && \
    chmod +x /usr/local/bin/infinito

CMD sh -c "infinito --help && exec tail -f /dev/null"
