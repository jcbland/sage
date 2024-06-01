#! /usr/bin/env bash
set -e
shopt -s extglob
##
## Write a Dockerfile for portability testing to stdout.
##
## This script needs to be run from SAGE_ROOT (root of the Sage repository).
## It is called by $SAGE_ROOT/tox.ini for all environments 'tox -e docker-...'
##
## Positional arguments:
##
SYSTEM="${1:-debian}"
SAGE_PACKAGE_LIST_ARGS="${2:-:standard:}"
WITH_SYSTEM_SPKG="${3:-yes}"
IGNORE_MISSING_SYSTEM_PACKAGES="${4:-no}"
EXTRA_SAGE_PACKAGES="${5:-_bootstrap}"
##
## Environment variables that take influence:
##
## - BOOTSTRAP
## - CONFIGURE_ARGS
## - DEVTOOLSET
## - DIST_UPGRADE
## - DOCKER_BUILDKIT
## - EXTRA_PATH
## - EXTRA_REPOSITORIES
## - EXTRA_SYSTEM_PACKAGES
## - FULL_BASE_IMAGE_AND_TAG
## - SKIP_SYSTEM_PKG_INSTALL
## - USE_CONDARC
## - __CHOWN
## - __SUDO
##
STRIP_COMMENTS="sed s/#.*//;"
SAGE_ROOT=.
export PATH="$SAGE_ROOT"/build/bin:$PATH
SYSTEM_PACKAGES=$EXTRA_SYSTEM_PACKAGES
SYSTEM_CONFIGURE_ARGS="--enable-option-checking "
for SPKG in $(sage-package list --has-file=spkg-configure.m4 $SAGE_PACKAGE_LIST_ARGS) $EXTRA_SAGE_PACKAGES; do
    SYSTEM_PACKAGE=$(sage-get-system-packages $SYSTEM $SPKG)
    if [ -n "${SYSTEM_PACKAGE}" ]; then
        # SYSTEM_PACKAGE can be empty if, for example, the environment
        # variable ENABLE_SYSTEM_SITE_PACKAGES is empty.
        for a in $SYSTEM_PACKAGE; do
            # shell-quote package if necessary
            SYSTEM_PACKAGES+=$(printf " %q" "$a")
        done
        SYSTEM_CONFIGURE_ARGS+="--with-system-${SPKG}=${WITH_SYSTEM_SPKG} "
    fi
done
echo "# Automatically generated by SAGE_ROOT/.ci/write-dockerfile.sh"
echo "# the :comments: separate the generated file into sections"
echo "# to simplify writing scripts that customize this file"
ADD="ADD $__CHOWN"
RUN=RUN
cat <<EOF
ARG BASE_IMAGE=$(eval echo "${FULL_BASE_IMAGE_AND_TAG}")
FROM \${BASE_IMAGE} as with-system-packages
EOF
case $SYSTEM in
    debian*|ubuntu*)
        if [ -n "$__SUDO" ]; then
            SUDO="sudo"
        else
            unset SUDO
        fi
        EXISTS="2>/dev/null >/dev/null apt-cache show"
        UPDATE="$SUDO apt-get update &&"
        INSTALL="$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -qqq --no-install-recommends --yes"
        CLEAN="&& $SUDO apt-get clean"
        if [ -n "$EXTRA_PATH" ]; then
            RUN="RUN export PATH=$EXTRA_PATH:\$PATH && "
        fi
        case "$SKIP_SYSTEM_PKG_INSTALL" in
            1|y*|Y*)
                ;;
            *)
                #
                # The Ubuntu Docker images are "minimized", meaning that some large
                # bits such as documentation has been removed. We have to unminimize
                # once (which reinstalls the full versions of some minimized packages),
                # or e.g. the maxima documentation (which we depend on for correct operation)
                # will be missing.
                #
                # But we only have to do this once. To save time in incremental builds,
                # we remove the unminimize binary here after it has done its job.
                #
                cat <<EOF
RUN if command -v unminimize > /dev/null; then  \
        (yes | unminimize) || echo "(ignored)"; \
        rm -f "\$(command -v unminimize)";       \
    fi
EOF
                if [ -n "$DIST_UPGRADE" ]; then
                    cat <<EOF
RUN sed -i.bak $DIST_UPGRADE /etc/apt/sources.list && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y dist-upgrade
EOF
                fi
                if [ -n "$EXTRA_REPOSITORIES" ]; then
                    cat <<EOF
RUN $UPDATE $INSTALL software-properties-common && ($INSTALL gpg gpg-agent || echo "(ignored)")
EOF
                    for repo in $EXTRA_REPOSITORIES; do
                        cat <<EOF
RUN $SUDO add-apt-repository $repo
EOF
                    done
                fi
        esac
        ;;
    fedora*|redhat*|centos*)
        EXISTS="2>/dev/null >/dev/null yum install -y --downloadonly"
        INSTALL="yum install -y"
        if [ -n "$DEVTOOLSET" ]; then
            case "$SKIP_SYSTEM_PKG_INSTALL" in
                1|y*|Y*)
                    ;;
                *)
                    cat <<EOF
RUN $INSTALL centos-release-scl
RUN $INSTALL devtoolset-$DEVTOOLSET
EOF
            esac
            RUN="RUN . /opt/rh/devtoolset-$DEVTOOLSET/enable && "
        fi
        ;;
    gentoo*)
        EXISTS="2>/dev/null >/dev/null emerge -f"
        UPDATE="" # not needed. "FROM gentoo/portage" used instead
        INSTALL="emerge -DNut --with-bdeps=y --complete-graph=y"
        ;;
    slackware*)
        # https://docs.slackware.com/slackbook:package_management
        # slackpkg install ignores packages that it does not know, so we do not have to filter
        EXISTS="true"
        UPDATE="(yes|slackpkg update) &&"
        INSTALL="slackpkg install"
        ;;
    arch*)
        # https://hub.docker.com/_/archlinux/
        UPDATE="pacman -Sy &&"
        EXISTS="pacman -Si"
        INSTALL="pacman -Su --noconfirm"
        cat <<EOF
RUN sed -i '/^NoExtract/d' /etc/pacman.conf
EOF
        ;;
    nix*)
        # https://hub.docker.com/r/nixos/nix
        case "$SKIP_SYSTEM_PKG_INSTALL" in
            1|y*|Y*)
                ;;
            *)
                cat <<EOF
RUN nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
RUN nix-channel --update
ENV PACKAGES="$SYSTEM_PACKAGES"
EOF
        esac
        INSTALL="nix-env --install"
        RUN="RUN nix-shell --packages \$PACKAGES --run "\'
        ENDRUN=\'
        ;;
    void*)
        UPDATE="xbps-install -Suy &&"
        EXISTS="xbps-query -R"
        INSTALL="xbps-install --yes"
        ;;
    opensuse*)
        UPDATE="zypper refresh &&"
        EXISTS="zypper --quiet install --no-confirm --auto-agree-with-licenses --no-recommends --download-only > /dev/null"
        INSTALL="zypper --ignore-unknown install --no-confirm --auto-agree-with-licenses --no-recommends --details"
        ;;
    conda*)
        case "$SKIP_SYSTEM_PKG_INSTALL" in
            1|y*|Y*)
                ;;
            *)
                cat <<EOF
ARG USE_CONDARC=${USE_CONDARC-condarc.yml}
ADD *condarc*.yml /tmp/
RUN echo \${CONDARC}; cd /tmp && conda config --stdin < \${USE_CONDARC}
RUN conda update -n base conda
RUN ln -sf /bin/bash /bin/sh
EOF
        esac
        # On this image, /bin/sh -> /bin/dash;
        # but some of the scripts in /opt/conda/etc/conda/activate.d
        # from conda-forge (as of 2020-01-27) contain bash-isms:
        # /bin/sh: 5: /opt/conda/etc/conda/activate.d/activate-binutils_linux-64.sh: Syntax error: "(" unexpected
        # The command '/bin/sh -c . /opt/conda/etc/profile.d/conda.sh; conda activate base;  ./bootstrap' returned a non-zero code
        # We just change the link to /bin/bash.
        INSTALL="conda install --update-all --quiet --yes"
        EXISTS="2>/dev/null >/dev/null conda search -f"
        #EXISTS="conda search -f"
        CLEAN="&& conda info; conda list"
        RUN="RUN . /opt/conda/etc/profile.d/conda.sh; conda activate base; "  # to activate the conda env
        ;;
    *)
        cat <<EOF
ARG BASE_IMAGE
FROM \${BASE_IMAGE} as with-system-packages
EOF
        INSTALL=$(sage-print-system-package-command $SYSTEM install " ")
        ;;
esac

case "$SKIP_SYSTEM_PKG_INSTALL" in
 1|y*|Y*)
  ;;

 *)
  cat <<EOF
#:packages:
EOF
  case "$IGNORE_MISSING_SYSTEM_PACKAGES" in
    no)
        cat <<EOF
RUN $UPDATE $INSTALL $SYSTEM_PACKAGES $CLEAN
EOF
        ;;
    yes)
        if [ -n "$EXISTS" ]; then
            # Filter by existing packages, try to install these in one shot; fall back to one by one.
            cat <<EOF
RUN $UPDATE EXISTING_PACKAGES=""; for pkg in $SYSTEM_PACKAGES; do echo -n .; if $EXISTS \$pkg; then EXISTING_PACKAGES="\$EXISTING_PACKAGES \$pkg"; echo -n "\$pkg"; fi; done; $INSTALL \$EXISTING_PACKAGES || (echo "Trying again one by one:"; for pkg in \$EXISTING_PACKAGES; do echo "Trying to install \$pkg"; $INSTALL \$pkg || echo "(ignoring error)"; done); : $CLEAN
EOF
        else
            # Try in one shot, fall back to one by one.  Separate "RUN" commands
            # for caching by docker.
            cat <<EOF
RUN $UPDATE $INSTALL $SYSTEM_PACKAGES || echo "(ignoring error)"
EOF
            for pkg in $SYSTEM_PACKAGES; do
                cat <<EOF
RUN $INSTALL $pkg || echo "(ignoring error)"
EOF
            done
            if [ -n "$CLEAN" ]; then
                cat <<EOF
RUN : $CLEAN
EOF
            fi
        fi
        ;;
    *)
        echo "Argument IGNORE_MISSING_SYSTEM_PACKAGES must be yes or no"
        ;;
  esac
esac

case ${DOCKER_BUILDKIT-0} in
    1)
        # With buildkit we cannot retrieve failed builds.
        # So we do not allow the main step of a build stage to fail.
        # Instead we record the exit code in the file STATUS.
        THEN_SAVE_STATUS='; echo $? > STATUS'
        # ... and at the beginning of the next build stage,
        # we check the status and exit with an error status.
        CHECK_STATUS_THEN='STATUS=$(cat STATUS 2>/dev/null); case "$STATUS" in ""|0) ;; *) exit $STATUS;; esac; '
esac

cat <<EOF

FROM with-system-packages as bootstrapped
#:bootstrapping:
$ADD Makefile VERSION.txt COPYING.txt condarc.yml README.md bootstrap bootstrap-conda configure.ac sage .homebrew-build-env tox.ini Pipfile.m4 .gitignore /new/
$ADD config/config.rpath /new/config/config.rpath
$ADD src/doc/bootstrap /new/src/doc/bootstrap
$ADD src/bin /new/src/bin
$ADD src/Pipfile.m4 src/pyproject.toml src/requirements.txt.m4 src/setup.cfg.m4 src/VERSION.txt /new/src/
$ADD m4 /new/m4
$ADD pkgs /new/pkgs
$ADD build /new/build
$ADD .upstream.d /new/.upstream.d
ADD .ci /.ci
RUN if [ -d /sage ]; then                                               \
        echo "### Incremental build from \$(cat /sage/VERSION.txt)" &&  \
        printf '/src\n!/src/doc/bootstrap\n!/src/bin\n!/src/*.m4\n!/src/*.toml\n!/src/VERSION.txt\n' >> /sage/.gitignore && \
        printf '/src\n!/src/doc/bootstrap\n!/src/bin\n!/src/*.m4\n!/src/*.toml\n!/src/VERSION.txt\n' >> /new/.gitignore && \
        if ! (cd /new && /.ci/retrofit-worktree.sh worktree-image /sage); then \
            echo "retrofit-worktree.sh failed, falling back to replacing /sage"; \
            for a in local logs; do                                     \
                if [ -d /sage/\$a ]; then mv /sage/\$a /new/; fi;       \
            done;                                                       \
            rm -rf /sage;                                               \
            mv /new /sage;                                              \
        fi;                                                             \
    else                                                                \
        mv /new /sage;                                                  \
    fi
WORKDIR /sage

ARG BOOTSTRAP="${BOOTSTRAP-./bootstrap}"
$RUN sh -x -c "\${BOOTSTRAP}" $ENDRUN $THEN_SAVE_STATUS

FROM bootstrapped as configured
#:configuring:
RUN $CHECK_STATUS_THEN mkdir -p logs/pkgs; rm -f config.log; ln -s logs/pkgs/config.log config.log
ARG CONFIGURE_ARGS="${CONFIGURE_ARGS:---enable-build-as-root}"
EOF
if [ ${WITH_SYSTEM_SPKG} = "force" ]; then
    cat <<EOF
$RUN ./configure $SYSTEM_CONFIGURE_ARGS \${CONFIGURE_ARGS} || (echo "::group::config.log"; cat config.log; echo "::endgroup::"; echo "********** configuring without forcing ***********"; ./configure \${CONFIGURE_ARGS}; echo "::group::config.log"; cat config.log; echo "::endgroup::"; exit 1) $ENDRUN $THEN_SAVE_STATUS
EOF
else
    cat <<EOF
$RUN ./configure $SYSTEM_CONFIGURE_ARGS \${CONFIGURE_ARGS} || (echo "::group::config.log"; cat config.log; echo "::endgroup::"; exit 1) $ENDRUN $THEN_SAVE_STATUS
EOF
fi
cat <<EOF

FROM configured as with-base-toolchain
# We first compile base-toolchain because otherwise lots of packages are missing their dependency on 'patch'
ARG NUMPROC=8
ENV MAKE="make -j\${NUMPROC}"
ARG USE_MAKEFLAGS="-k V=0"
ENV SAGE_CHECK=warn
ENV SAGE_CHECK_PACKAGES="!cython,!r,!python3,!gap,!cysignals,!linbox,!git,!ppl,!cmake,!rpy2,!sage_sws2rst"
#:toolchain:
$RUN $CHECK_STATUS_THEN make \${USE_MAKEFLAGS} base-toolchain $ENDRUN $THEN_SAVE_STATUS

FROM with-base-toolchain as with-targets-pre
ARG NUMPROC=8
ENV MAKE="make -j\${NUMPROC}"
ARG USE_MAKEFLAGS="-k V=0"
ENV SAGE_CHECK=warn
ENV SAGE_CHECK_PACKAGES="!cython,!r,!python3,!gap,!cysignals,!linbox,!git,!ppl,!cmake,!rpy2,!sage_sws2rst"
#:make:
ARG TARGETS_PRE="all-sage-local"
$RUN $CHECK_STATUS_THEN make SAGE_SPKG="sage-spkg -y -o" \${USE_MAKEFLAGS} \${TARGETS_PRE} $ENDRUN $THEN_SAVE_STATUS

FROM with-targets-pre as with-targets
ARG NUMPROC=8
ENV MAKE="make -j\${NUMPROC}"
ARG USE_MAKEFLAGS="-k V=0"
ENV SAGE_CHECK=warn
ENV SAGE_CHECK_PACKAGES="!cython,!r,!python3,!gap,!cysignals,!linbox,!git,!ppl,!cmake,!rpy2,!sage_sws2rst"
$ADD .gitignore /new/.gitignore
$ADD src /new/src
ADD .ci /.ci
RUN cd /new && rm -rf .git && \
    if /.ci/retrofit-worktree.sh worktree-pre /sage; then \
        cd /sage && touch configure build/make/Makefile; \
    else \
        echo "retrofit-worktree.sh failed, falling back to replacing /sage/src"; \
        rm -rf /sage/src;                                    \
        mv src /sage/src;                                    \
        cd /sage && ./bootstrap && ./config.status;          \
    fi

ARG TARGETS="build"
$RUN $CHECK_STATUS_THEN make SAGE_SPKG="sage-spkg -y -o" \${USE_MAKEFLAGS} \${TARGETS} $ENDRUN $THEN_SAVE_STATUS

FROM with-targets as with-targets-optional
ARG NUMPROC=8
ENV MAKE="make -j\${NUMPROC}"
ARG USE_MAKEFLAGS="-k V=0"
ENV SAGE_CHECK=warn
ENV SAGE_CHECK_PACKAGES="!cython,!r,!python3,!gap,!cysignals,!linbox,!git,!ppl,!cmake,!rpy2,!sage_sws2rst"
ARG TARGETS_OPTIONAL="ptest"
$RUN $CHECK_STATUS_THEN make SAGE_SPKG="sage-spkg -y -o" \${USE_MAKEFLAGS} \${TARGETS_OPTIONAL} || echo "(error ignored)" $ENDRUN $THEN_SAVE_STATUS

#:end:
EOF
