# External answer key: MaE examples

Source: MaE dataset, Otero, Druga and Lan (2024), MIT licence. Examples were written by learning researchers from published sources (mostly Ashlock 2006); they are not raw student data.

- In scope: 36 of 40 examples (simplifying is not a topic of this tool).
- Reproduced exactly by a wrong rule in the library: 31 of 36.
- Right answer reached by a wrong rule (the correct answer trap, inside MaE itself): 2 examples (MaE14 ex 1, MaE14 ex 2).
- Leave-one-out: the engine committed on 23 of 35 held-out examples and predicted the student's exact answer on 23 of those. It gave no diagnosis on 12.

## Every example

| MaE | Ex | Topic | Problem | Student wrote | Correct | Rules that give the student's answer |
|---|---|---|---|---|---|---|
| MaE07 | 1 | out of scope | simplify 4/8 | 2/8 |  | none |
| MaE07 | 2 | out of scope | simplify 6/8 | 3/8 |  | none |
| MaE07 | 3 | out of scope | simplify 4/6 | 1/6 |  | none |
| MaE07 | 4 | out of scope | simplify 7/7 | 1/7 |  | none |
| MaE08 | 1 | fractions | 4/5 + 2/3 | 6/8 | 1 7/15 | frac_add_tops_add_bottoms |
| MaE08 | 2 | fractions | 1/4 + 2/3 | 3/7 | 11/12 | frac_add_tops_add_bottoms |
| MaE08 | 3 | fractions | 5/12 + 3/8 | 8/20 | 19/24 | frac_add_tops_add_bottoms |
| MaE08 | 4 | frac_sub | 8 - 3/5 | 5/3 | 7 2/5 | none |
| MaE09 | 1 | fractions | 1/2 + 1/4 | 2/4 | 3/4 | frac_add_tops_keep_larger_bottom, frac_common_bottom_no_scaling |
| MaE09 | 2 | fractions | 2/5 + 1/2 | 3/10 | 9/10 | frac_add_tops_multiply_bottoms, frac_common_bottom_no_scaling |
| MaE09 | 3 | fractions | 3/5 + 1/3 | 4/15 | 14/15 | frac_add_tops_multiply_bottoms, frac_common_bottom_no_scaling |
| MaE09 | 4 | fractions | 3/4 + 1/2 | 4/4 | 1 1/4 | frac_add_tops_keep_larger_bottom, frac_common_bottom_no_scaling, frac_add_tops_keep_first_bottom |
| MaE10 | 1 | frac_sub | 7 - 1/3 | 2 | 6 2/3 | none |
| MaE10 | 2 | frac_sub | 8 1/3 - 2/3 | 4 1/2 | 7 2/3 | none |
| MaE10 | 3 | frac_sub | 6 - 1 1/4 | 5 1/4 | 4 3/4 | sub_smaller_from_larger |
| MaE10 | 4 | frac_sub | 1 - 1/3 | 1 1/3 | 2/3 | sub_smaller_from_larger |
| MaE11 | 1 | frac_sub | 6 2/3 - 3 1/6 | 3 1/3 | 3 1/2 | sub_parts_separately |
| MaE11 | 2 | frac_sub | 4 5/8 - 1 3/4 | 3 2/4 | 2 7/8 | sub_parts_separately |
| MaE11 | 3 | frac_sub | 5 3/8 - 2 2/3 | 3 1/5 | 2 17/24 | sub_parts_separately |
| MaE11 | 4 | frac_sub | 7 2/5 - 4 7/10 | 3 5/5 | 2 7/10 | sub_parts_separately |
| MaE13 | 1 | frac_mul | 2/3 × 3 | 6/9 | 2 | mul_whole_scales_both |
| MaE13 | 2 | frac_mul | 1/4 × 6 | 6/24 | 1 1/2 | mul_whole_scales_both |
| MaE13 | 3 | frac_mul | 4/5 × 2 | 8/10 | 1 3/5 | mul_whole_scales_both |
| MaE13 | 4 | frac_mul | 3/8 × 4 | 12/32 | 1 1/2 | mul_whole_scales_both |
| MaE14 | 1 | frac_div | 4/6 ÷ 2/2 | 2/3 | 2/3 | div_correct, div_across_drop_remainder, div_multiplies_instead |
| MaE14 | 2 | frac_div | 6/8 ÷ 2/8 | 3/1 | 3 | div_correct, div_across_drop_remainder |
| MaE14 | 3 | frac_div | 6/10 ÷ 2/4 | 3/2 | 1 1/5 | div_across_drop_remainder |
| MaE14 | 4 | frac_div | 7/5 ÷ 3/2 | 2/2 | 14/15 | div_across_drop_remainder |
| MaE15 | 1 | frac_div | 2/3 ÷ 3/8 | 9/16 | 1 7/9 | div_flip_first |
| MaE15 | 2 | frac_div | 2/5 ÷ 1/3 | 5/6 | 1 1/5 | div_flip_first |
| MaE15 | 3 | frac_div | 3/4 ÷ 1/5 | 4/15 | 3 3/4 | div_flip_first |
| MaE15 | 4 | frac_div | 5/8 ÷ 2/3 | 16/15 | 15/16 | div_flip_first |
| MaE18 | 1 | integers | -8 + 6 | 2 | -2 | int_always_positive |
| MaE18 | 2 | integers | 5 + (-9) | 4 | -4 | int_always_positive, int_sign_of_first |
| MaE18 | 3 | integers | 7 + (-2) | -5 | 5 | none |
| MaE18 | 4 | integers | 4 + (-3) | 7 | 1 | int_plus_negative_is_plus |
| MaE19 | 1 | integers | -6 + (-8) | 2 | -14 | int_plus_negative_is_plus, int_leading_minus_covers_all |
| MaE19 | 2 | integers | -8 + (-3) | 5 | -11 | none |
| MaE19 | 3 | integers | -4 + (-3) | 7 | -7 | int_two_negatives_make_positive, int_always_positive |
| MaE19 | 4 | integers | -2 + (-5) | 7 | -7 | int_two_negatives_make_positive, int_always_positive |

## Leave-one-out

| MaE | Held out | Engine's choice | Confidence | Predicted | Actual | Match |
|---|---|---|---|---|---|---|
| MaE08 | 1 | frac_add_tops_add_bottoms | 0.982 | 3/4 | 6/8 | yes |
| MaE08 | 2 | frac_add_tops_add_bottoms | 0.982 | 3/7 | 3/7 | yes |
| MaE08 | 3 | frac_add_tops_add_bottoms | 0.983 | 2/5 | 8/20 | yes |
| MaE09 | 1 | frac_common_bottom_no_scaling | 0.992 | 1/2 | 2/4 | yes |
| MaE09 | 2 | frac_common_bottom_no_scaling | 0.992 | 3/10 | 3/10 | yes |
| MaE09 | 3 | frac_common_bottom_no_scaling | 0.992 | 4/15 | 4/15 | yes |
| MaE09 | 4 | frac_common_bottom_no_scaling | 0.992 | 1 | 4/4 | yes |
| MaE10 | 1 | no diagnosis | 0.74 | - | 2 | - |
| MaE10 | 2 | no diagnosis | 0.74 | - | 4 1/2 | - |
| MaE10 | 3 | no diagnosis | 0.984 | - | 5 1/4 | - |
| MaE10 | 4 | no diagnosis | 0.984 | - | 1 1/3 | - |
| MaE11 | 1 | sub_parts_separately | 0.998 | 3 1/3 | 3 1/3 | yes |
| MaE11 | 2 | sub_parts_separately | 0.998 | 3 1/2 | 3 2/4 | yes |
| MaE11 | 3 | sub_parts_separately | 0.998 | 3 1/5 | 3 1/5 | yes |
| MaE11 | 4 | sub_parts_separately | 0.998 | 4 | 3 5/5 | yes |
| MaE13 | 1 | mul_whole_scales_both | 0.999 | 2/3 | 6/9 | yes |
| MaE13 | 2 | mul_whole_scales_both | 0.999 | 1/4 | 6/24 | yes |
| MaE13 | 3 | mul_whole_scales_both | 0.999 | 4/5 | 8/10 | yes |
| MaE13 | 4 | mul_whole_scales_both | 0.999 | 3/8 | 12/32 | yes |
| MaE14 | 1 | div_across_drop_remainder | 0.998 | 2/3 | 2/3 | yes |
| MaE14 | 2 | div_across_drop_remainder | 0.998 | 3 | 3/1 | yes |
| MaE14 | 3 | div_across_drop_remainder | 0.976 | 1 1/2 | 3/2 | yes |
| MaE14 | 4 | div_across_drop_remainder | 0.976 | 1 | 2/2 | yes |
| MaE15 | 1 | div_flip_first | 0.998 | 9/16 | 9/16 | yes |
| MaE15 | 2 | div_flip_first | 0.998 | 5/6 | 5/6 | yes |
| MaE15 | 3 | div_flip_first | 0.998 | 4/15 | 4/15 | yes |
| MaE15 | 4 | div_flip_first | 0.998 | 1 1/15 | 16/15 | yes |
| MaE18 | 1 | no diagnosis | 0.991 | - | 2 | - |
| MaE18 | 2 | no diagnosis | 0.991 | - | 4 | - |
| MaE18 | 3 | no diagnosis | 0.615 | - | -5 | - |
| MaE18 | 4 | no diagnosis | 0.617 | - | 7 | - |
| MaE19 | 1 | no diagnosis | 0.383 | - | 2 | - |
| MaE19 | 2 | no diagnosis | 0.381 | - | 5 | - |
| MaE19 | 3 | no diagnosis | 0.965 | - | 7 | - |
| MaE19 | 4 | no diagnosis | 0.982 | - | 7 | - |
