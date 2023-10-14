runc_path="$1"
debug="$2"

PPpackage-runner "$runc_path" $debug >/dev/null &
echo $!
