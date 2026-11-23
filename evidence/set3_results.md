# Held-out set 3: wrong rules the tool has never seen

Written after the design was frozen (commit 377934c) and committed (1d4d7f8) before this test was first run. Run once; nothing was changed afterwards. 200 simulated students per rule, no slips. The only correct result is 'no diagnosis'.

| Rule | Sessions | No diagnosis % (correct) | Wrong rule named % | False all-clear % | Mean questions |
|---|---|---|---|---|---|
| h3_int_signs_differ_add_sizes_sign_of_larger | 200 | 100.0 | 0.0 | 0.0 | 6.17 |
| h3_int_minus_negative_answer_negative | 200 | 100.0 | 0.0 | 0.0 | 5.25 |
| h3_frac_cross_tops_add_bottoms | 200 | 100.0 | 0.0 | 0.0 | 5 |
| h3_frac_multiply_tops_add_bottoms | 200 | 100.0 | 0.0 | 0.0 | 5 |
| h3_sub_borrow_ten | 200 | 99.0 | 1.0 | 0.0 | 5.41 |
| h3_sub_regroup_keeps_whole | 200 | 100.0 | 0.0 | 0.0 | 5.05 |
| h3_mul_whole_adds_to_top | 200 | 91.0 | 0.0 | 9.0 | 4.84 |
| h3_mul_adds_across | 200 | 100.0 | 0.0 | 0.0 | 5 |
| h3_div_tops_keep_first_bottom | 200 | 100.0 | 0.0 | 0.0 | 5 |
| h3_div_times_second_bottom | 200 | 100.0 | 0.0 | 0.0 | 5.08 |
| **ALL** | 2000 | 99.0 | 0.1 | 0.9 | 5.18 |
