#!/bin/bash
#
# Download the status of Montreal's Bixi stations.
# Save it in a AAAA-MM-DD_HH:MM:SS.xml.bz2 file where AAAA, MM, DD, HH, MM, SS reprensents date/time.
#
# User should adjust output_directory

# CHANGE THIS VARIABLE HERE
# Output directory
output_dir=~/bixi

mkdir -p $output_dir
cd $output_dir

temp_file=$(mktemp)
date_time=$(date +\%Y-\%m-\%d_\%H:\%M:00).xml
wget https://montreal.bixi.com/data/bikeStations.xml -q -O $temp_file
mv $temp_file $date_time
bzip2 $date_time
