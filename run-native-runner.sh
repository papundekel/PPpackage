run_path="$1"
workdirs_path="$2"
debug="$3"

python -m PPpackage_runner "$run_path" "$workdirs_path" $debug >/dev/null &
echo $!
