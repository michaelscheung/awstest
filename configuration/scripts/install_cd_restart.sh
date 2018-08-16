command='sudo echo "* * * * * /sbin/service codedeploy-agent start" >> /var/spool/cron/root'
for host in $(cat ~/prog/eshade/data/servers.txt); do
    echo "Running on host $host"
    ssh -o StrictHostKeyChecking=no ec2-user@"$host" "$command" >"output.$host";
  done
