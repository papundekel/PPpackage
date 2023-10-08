runc_path="$1"
debug="$2"

PPpackage-runc "$runc_path" $debug >/dev/null &
echo $!
