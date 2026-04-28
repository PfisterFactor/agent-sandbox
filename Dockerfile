FROM fedora:latest

ENV SHELL=/usr/bin/zsh \
    HOME=/root \
    LANG=C.UTF-8

RUN dnf install -y git zsh ncurses ncurses-term \
 && dnf clean all \
 && usermod -s /usr/bin/zsh root \
 && git clone --depth 1 https://github.com/PfisterFactor/term-ide /usr/local/src/term-ide

RUN bash /usr/local/src/term-ide/install.sh

RUN infocmp ghostty >/dev/null

WORKDIR /root
CMD ["/usr/bin/zsh", "-l"]
