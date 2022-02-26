sum_point=0
sum_con=0
for d in *; do
  #echo $d
  for f in $d/all_config*; do
    np=$(bash datamining.bash $f) # np: number of points
    sum_point=$(( $sum_point + $np ))
    confile=$(echo $f | sed "s/all_config/conflict/g") #conflict file
    confile=$confile".txt"
    #echo $confile
    nc=$(bash datamining_conflict.bash $np $confile) #nc: number of (potential) conflicts
    sum_con=$(( $sum_con + $nc ))
    echo "the number of experiments points, sum_point = $sum_point, the number of potential conflicts (anomalies) therein, sum_con = $sum_con"
    #echo "the number of experiment points, sum_point = $sum_point, the number of potential conflicts therein, sum_con = $sum_con"
  done
done
