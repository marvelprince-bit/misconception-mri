# Held-out set 4: wrong rules the tool has never seen

Written after the design was frozen (commit aacb5fd) and committed before this test was first run. Run once; nothing was changed afterwards. 200 simulated students per rule, no slips. The only correct result is 'no diagnosis'.

| Rule | Sessions | No diagnosis % (correct) | Wrong rule named % | False all-clear % | Mean questions |
|---|---|---|---|---|---|
| h4_int_subtract_smaller_from_larger | 200 | 100.0 | 0.0 | 0.0 | 6.43 |
| h4_int_drops_first_minus_when_adding_positive | 200 | 100.0 | 0.0 | 0.0 | 8.53 |
| h4_int_positive_plus_negative_keeps_plus | 200 | 100.0 | 0.0 | 0.0 | 9.19 |
| h4_frac_scales_tops_by_own_bottom | 200 | 99.5 | 0.0 | 0.5 | 5.33 |
| h4_frac_same_bottoms_adds_bottoms | 200 | 100.0 | 0.0 | 0.0 | 8 |
| h4_sub_whole_minus_mixed_brings_down_fraction | 200 | 100.0 | 0.0 | 0.0 | 8.64 |
| h4_sub_improper_multiplies_by_top | 200 | 100.0 | 0.0 | 0.0 | 5 |
| h4_sub_keeps_larger_bottom | 200 | 100.0 | 0.0 | 0.0 | 5.11 |
| h4_mul_same_bottoms_keeps_bottom | 200 | 100.0 | 0.0 | 0.0 | 5.01 |
| h4_mul_common_bottom_first | 200 | 100.0 | 0.0 | 0.0 | 5.02 |
| h4_div_bigger_by_smaller | 200 | 100.0 | 0.0 | 0.0 | 6.79 |
| h4_div_common_bottom_keeps_bottom | 200 | 100.0 | 0.0 | 0.0 | 5 |
| **ALL** | 2400 | 100.0 | 0.0 | 0.0 | 6.5 |
