#!/bin/bash
# Defines constants related to the xen system




#LXVERSION="3.16.0-4-amd64"
LXVERSION="4.9.0-13-amd64"

LIT_BEHAVIOUR="
on_poweroff = 'destroy'
on_reboot = 'restart'
on_crash = 'restart'
"

LIT_MACHINE_STATIC="
kernel = '/boot/vmlinuz-${LXVERSION}'
extra  = 'elevator=noop'
ramdisk = '/boot/initrd.img-${LXVERSION}'
vcpus  = '1'
memory = '256'
maxmem = '256'
root   = '/dev/xvda1 ro'
"
