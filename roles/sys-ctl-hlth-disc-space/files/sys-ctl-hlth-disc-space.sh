#!/bin/sh
# @param $1 mimimum free disc space
errors=0
minimum_percent_cleanup_disc_space="$1"
echo "checking disc space use..."
df
for disc_use_percent in $(df --output=pcent | sed 1d)
do
    disc_use_percent_number=$(echo "$disc_use_percent" | sed "s/%//")
    if [ "$disc_use_percent_number" -gt "$minimum_percent_cleanup_disc_space" ]; then
      echo "WARNING: $disc_use_percent_number exceeds the limit of $minimum_percent_cleanup_disc_space%."
      errors+=1;
    fi
done
exit $errors;