FROM fedora:latest

ENV SHELL=/usr/bin/zsh \
    HOME=/root \
    LANG=C.UTF-8

RUN dnf install -y git zsh ncurses \
 && dnf clean all \
 && usermod -s /usr/bin/zsh root \
 && git clone --depth 1 https://github.com/PfisterFactor/term-ide /usr/local/src/term-ide

RUN bash /usr/local/src/term-ide/install.sh

# Ghostty's real terminfo (rendered from upstream's Zig source by
# scripts/render_ghostty_terminfo.py). The ncurses-term bundled entry is a
# 13-cap stub missing kbs/cub1/etc., which breaks backspace and arrow keys.
COPY ghostty.terminfo /tmp/ghostty.terminfo
RUN tic -x /tmp/ghostty.terminfo \
 && rm /tmp/ghostty.terminfo \
 && infocmp ghostty | grep -q 'kbs='

WORKDIR /root
CMD ["/usr/bin/zsh", "-l"]
