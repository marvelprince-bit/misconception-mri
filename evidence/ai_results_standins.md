# AI rule-writer results with stand-in writers (no live model)

Generated on commit 20b9b69 by `python scripts/evaluate_ai.py --writer <name> --seeds 20` (students 0 to 19, used during development) and `--seed-offset 100` (students 100 to 119, never used during development). One wrong rule is removed from the tool's list and a simulated student follows it. The AI is only called when no known rule fits. Earlier versions of this file are in git history.

- **oracle** writes the true rule (what a good model should do).
- **occam** replays the live Claude run's failure: it returns the SIMPLEST rule that fits the answers it is shown, using Claude's own two decoy rules (division and subtraction) before the true rule.
- **cheat** memorises the answers it was shown and does correct maths everywhere else (what the hidden-answer check exists to catch).
- **down** behaves like an AI service that cannot be reached.
- **messy** has the right idea but sloppy formatting; it fixes the code when asked to repair it.
- **partial** copies the student's rule only on the kinds of question where it saw wrong answers (integers only). It never generalises, so the correct outcome for it is no diagnosis, not a wrong one.
- **partial, shape check none** is the design before the shape check, for comparison.

## Students 0 to 19

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_oracle.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.81 | 0.0 | 0.0 |
| off | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.81 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_occam.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.82 | 0.0 | 0.0 |
| off | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.82 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_cheat.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 0.0 | None | 0.0 | 0.0 | 100.0 | 10.72 | 1.0 | 0.0 |
| off | 480 | 100.0 | 99.4 | 0.0 | 0.0 | 0.0 | 100.0 | 10.01 | 0.6 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_down.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 0.0 | None | 0.0 | 0.0 | 100.0 | 7.73 | 0.0 | 0.0 |
| off | 480 | 100.0 | 0.0 | None | 0.0 | 0.0 | 100.0 | 7.73 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_messy.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.81 | 100.0 | 100.0 |
| off | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.81 | 100.0 | 100.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_partial.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 140 | 100.0 | 91.4 | 46.9 | 42.9 | 0.0 | 57.1 | 18.44 | 0.0 | 0.0 |
| off | 140 | 100.0 | 100.0 | 42.9 | 42.9 | 0.0 | 57.1 | 18.43 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_partial_nonecheck.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 140 | 90.7 | 82.1 | 50.4 | 41.4 | 50.0 | 8.6 | 11.86 | 0.0 | 0.0 |
| off | 140 | 90.7 | 90.7 | 45.7 | 41.4 | 51.4 | 7.1 | 11.74 | 0.0 | 0.0 |

## Students 100 to 119

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_oracle_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.84 | 0.0 | 0.0 |
| off | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.84 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_occam_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.84 | 0.0 | 0.0 |
| off | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.84 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_cheat_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 0.0 | None | 0.0 | 0.0 | 100.0 | 10.72 | 1.0 | 0.0 |
| off | 480 | 100.0 | 99.2 | 0.0 | 0.0 | 0.0 | 100.0 | 10.01 | 0.8 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_down_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 0.0 | None | 0.0 | 0.0 | 100.0 | 7.73 | 0.0 | 0.0 |
| off | 480 | 100.0 | 0.0 | None | 0.0 | 0.0 | 100.0 | 7.73 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_messy_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.84 | 100.0 | 100.0 |
| off | 480 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 13.84 | 100.0 | 100.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_partial_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 140 | 100.0 | 87.9 | 48.0 | 42.1 | 0.0 | 57.9 | 18.11 | 0.0 | 0.0 |
| off | 140 | 100.0 | 100.0 | 42.9 | 42.9 | 0.0 | 57.1 | 18.32 | 0.0 | 0.0 |

Raw prompts and replies: /home/claude/misconception-mri/evidence/ai_raw_partial_nonecheck_seeds100-119.jsonl
| Hidden-answer check | sessions | ai_called_pct | admitted_pct | admitted_rules_truly_right_pct | final_right_pct | final_wrong_pct | final_no_diagnosis_pct | mean_questions | repair_used_pct | admitted_after_repair_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| on | 140 | 90.0 | 77.9 | 48.6 | 37.9 | 50.0 | 12.1 | 11.99 | 0.0 | 0.0 |
| off | 140 | 90.0 | 90.0 | 42.9 | 38.6 | 55.0 | 6.4 | 11.94 | 0.0 | 0.0 |

