#!/usr/bin/env bash
# render a list of segments: bash render_list.sh h|v "a:b a:b ..."
cd /home/user/do-my-task/docs-series/11-neutron-star-teaspoon
[[ $1 == v ]] && export NS_VERT=1
for ab in $2; do nice -n 5 python3 comp.py ${ab%:*} ${ab#*:} 2>&1 | grep -v -i warning || echo "FAILED $ab"; done
echo "list $1 done $(date)"
