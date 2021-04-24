#!/usr/bin/expect
set timeout 30
spawn /root/Desktop/SKEAF/skeaf
expect "Read"
send "y\r"
expect "correct"
send "y\r"
interact