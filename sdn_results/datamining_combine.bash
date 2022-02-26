sum_point=0
sum_con=0
for f in *; do
#for f in random_smallworld_s20_h12_*; do
  np=$(bash datamining.bash $f/all_config) # np: number of points
  sum_point=$(( $sum_point + $np ))
  nc=$(bash datamining_conflict.bash $np $f/conflict.txt) #nc: number of (potential) conflicts
  sum_con=$(( $sum_con + $nc ))
  echo "sum_point = $sum_point, sum_con = $sum_con"
done
