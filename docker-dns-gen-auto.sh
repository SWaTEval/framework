#!/usr/bin/env sh
set -e

# This script is meant for quick & easy install via:
#   $ sudo sh -c "$(curl -fsSL https://raw.githubusercontent.com/jderusse/docker-dns-gen/master/bin/install)"

C1='\033[0;31m'
C2='\033[0;33m'
C3='\033[0;32m'
C4='\033[0;36m'
C5='\033[0;35m'
C0='\033[0m'

if [ "$(id -u)" -ne 0 ]; then
  echo "${C1}This script must be run by root${C0}"
  echo "${C2} running ${C3}sudo $0 $@${C0}"
  sudo $0 "$@"
  exit 0
fi

GATEWAY=$(ip -4 addr show docker0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "")
main () {
  requirements
  install
}

requirements () {
  echo "${C2}Requirements${C0}"
  requirements_packages
  requirements_services
  requirements_config
  requirements_legacy
  requirements_network
}

requirements_packages () {
  install_if_needed "resolvconf" "resolvconf" "yes"
  echo "${C5} - resolvconf is installed${C0}"
}

requirements_services () {
  docker info 2>/dev/null >/dev/null || (echo "${C1} - docker should be installed and usable by root user${C0}" && exit 1)
  echo "${C5} - ${C3}docker${C5} is installed${C0}"

  docker rm -fv dns-gen > /dev/null 2> /dev/null || true
  echo "${C5} - container ${C3}dns-gen${C5} stoped${C0}"
}

requirements_config () {
  sed -i "/# dns-gen/d" /etc/resolvconf/resolv.conf.d/head
  sed -i "/nameserver ${GATEWAY}/d" /etc/resolvconf/resolv.conf.d/head
  echo "${C5} - ${C3}resolv.conf${C5} cleaned${C0}"
}

requirements_legacy () {
  previous=$(cat /etc/NetworkManager/dnsmasq.d/01_docker 2>/dev/null|grep "127.0.0.1#54" > /dev/null && echo "1" || echo "")
  if ! [ -z "${previous}" ]; then
    if confirm "  Should I remove old dnsmasq.d/01_docker file?"; then
      rm /etc/NetworkManager/dnsmasq.d/01_docker
      service NetworkManager restart
      echo "${C5} - previous config ${C3}/etc/NetworkManager/dnsmasq.d/01_docker${C5} removed ${C0}"
    fi
  fi

  resolvconf -u
}

requirements_network () {
  ip -4 addr show docker0 2>/dev/null >/dev/null || (echo "${C1} - the docker0 interface does not exists${C0}" && exit 1)
  echo "${C5} - interface ${C3}docker0${C5} exists${C0}"

  used=$(nc -vz -u ${GATEWAY} 53 2>/dev/null && echo "1" || echo "")
  if [ -z "${used}" ]; then
    echo "${C5} - port ${C3}53${C5} is free${C0}"
  else
    echo "${C1} - port ${C3}53${C1} already used on ${C3}${GATEWAY}${C0}"
    exit 1
  fi
}

install () {
  echo "${C2}Install${C0}"
  install_container
  install_config
}

install_container () {
  docker pull jderusse/dns-gen:2
  docker run -d --name dns-gen \
        --restart always \
        --log-opt "max-size=10m" \
        --net host \
        -e GATEWAY=$GATEWAY \
        --volume /:/host:ro \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        jderusse/dns-gen:2 > /dev/null
  echo "${C5} - started container ${C3}dns-gen${C5}${C0}"
}

install_config () {
  # find insert position
  index=$(grep -n "^[^#;]" /etc/resolvconf/resolv.conf.d/head|head -n1|cut -d: -f1)
  line="nameserver ${GATEWAY} # dns-gen"
  if [ -z "${index}" ]; then
      echo "${line}" >> /etc/resolvconf/resolv.conf.d/head
      echo "${C5} - appended ${C3}${line}${C5} in ${C3}/etc/resolvconf/resolv.conf.d/head${C0}"
  else
      sed -i "${index}i${line}" /etc/resolvconf/resolv.conf.d/head
      echo "${C5} - inserted ${C3}${line}${C5} at position ${C3}${index}${C5} in ${C3}/etc/resolvconf/resolv.conf.d/head${C0}"
  fi

  resolvconf -u
}

install_if_needed () {
  command=${1}
  package=${2}
  reboot=${3:-""}
  if ! [ -x "$(command -v $1)" ]; then
    install_apt "${package}"
    if ! [ -z "${reboot}" ]; then
      echo ""
      echo " ${C1}+--------------------------------------------+"
      echo " ${C1}|                                            |${C0}"
      echo " ${C1}| You probably need to to reboot your system |${C0}"
      echo " ${C1}|                                            |${C0}"
      echo " ${C1}+--------------------------------------------+"
      echo ""
    fi
  fi
}

install_apt () {
  package=${1}
  echo " ${C1}This script requires ${C3}${package}${C0}"
  if confirm "  May I install it for you?"; then
    apt-get update
    apt-get install "${package}"
  else
    echo "  ${C1}Aborted${C0}"
    exit 1
  fi
}

confirm () {
  message=$1
  echo "${C4}${message}${C0}"
  while
   read -p "  " answer
  do
    case $answer in
      ([yY][eE][sS] | [yY]) return 0;;
      ([nN][oO] | [nN]) return 1;;
      (*) echo "${C4}${message}${C3} yes ${C4}or${C3} no${C0}";;
    esac
  done
}

main
