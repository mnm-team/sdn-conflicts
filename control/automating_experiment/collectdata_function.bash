#!/bin/bash

#function to calcualte absolute value
abs_old() { #doesn't work with decimal number
    [[ $[ $@ ] -lt 0 ]] && echo "$[ ($@) * -1 ]" || echo "$[ $@ ]"
} #note: The $[ ] syntax is deprecated. Please use $(( )) instead. See:http://mywiki.wooledge.org/ArithmeticExpression

#if (( $(bc <<<'1.4 < 2.5') )); then
#  echo '1.4 is less than 2.5.'
#fi
compare() { # input: 2 number a b, output: 1 if a < b; 0 if a >b
#  echo $1 $2
  if (( $(bc <<<"$1 < $2") )); then
    return 1
  else
    return 0
  fi
}

compareV2() { # input: 2 number a b, output: 1 if a < b; 0 if a >b
#  echo $1 $2
  if (( $(bc <<<"$1 < $2") )); then
    echo 1
  else
    echo 0
  fi
}

abs() {
  ret=$(bc <<< "$1 > 0")
  [ $ret -eq 1 ] && echo $1 || echo $(bc -l <<< "$1*-1")
}

alternative_port(){ #input a number
#generate alternative port for e.g., nc server if the chosen port is greater than 65535,
#the generated port must be greater than 10000 and less than 65535
  ret=$(($1%10000+10000))
  echo $ret
}
