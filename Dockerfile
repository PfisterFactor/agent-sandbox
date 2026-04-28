FROM fedora:latest

ENV SHELL=/usr/bin/zsh \
    HOME=/root \
    LANG=C.UTF-8

RUN dnf install -y git zsh ncurses \
 && dnf clean all \
 && usermod -s /usr/bin/zsh root \
 && git clone --depth 1 https://github.com/PfisterFactor/term-ide /usr/local/src/term-ide

RUN bash /usr/local/src/term-ide/install.sh

RUN curl -fsSL https://raw.githubusercontent.com/ghostty-org/ghostty/main/src/terminfo/ghostty.terminfo \
      -o /tmp/ghostty.terminfo \
 && tic -x /tmp/ghostty.terminfo \
 && rm /tmp/ghostty.terminfo

WORKDIR /root
CMD ["/usr/bin/zsh", "-l"]
