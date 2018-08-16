#!/bin/bash
echo "stopping server"
#pkill -f yolo --sig 15
echo `whoami`
echo `id`
echo `pgrep -f java8`

pid=`pgrep -f java8`
echo `pkill -f java8`

maxwait=300
i=0
while kill -0 $pid; do
    if [ $i -gt ${maxwait} ]; then
        echo "Error: Waited more than ${maxwait} seconds for process with pid ${pid} to die. Giving up." >&2
        exit 3
    fi

    i=$((i + 1))
    sleep 1
done

echo "Hopefully server stopped"
