# Rollout Verification Tools

This directory contains automated verification tools for safe production rollout.

## Safety Verification Script

**File**: `safety_verify.py`

Automated verification tool that checks all critical safety constraints before rollout.

### Features

The script performs 8 critical safety checks:

1. **Paper Pipeline Unchanged** - Verifies `paper_gate/*` has no forbidden imports
2. **Execution Unchanged** - Verifies `execution/*` has no forbidden imports  
3. **Risk Gates Unchanged** - Verifies `execution_safety/*` has no forbidden imports
4. **Frozen Model Intact** - Verifies model is not auto-retraining by default
5. **Adaptive Isolated** - Verifies adaptive module doesn't directly import execution
6. **Retry Guards Active** - Verifies retry guard module has required methods and config
7. **Idempotency Active** - Verifies side effect guards have required methods and config
8. **Config Defaults Safe** - Verifies all new features are disabled by default

### Usage

```bash
# Run verification from repository root
./scripts/rollout/safety_verify.py

# Or run with python
python3 scripts/rollout/safety_verify.py
```

### Exit Codes

- **0**: All safety checks passed ✓
- **1**: One or more safety checks failed ✗

### Example Output

```
2026-02-07 18:51:12 - INFO - Starting safety verification...
2026-02-07 18:51:12 - INFO - Running check: Paper Pipeline Unchanged
2026-02-07 18:51:12 - INFO - ✓ Paper Pipeline Unchanged - PASSED
...
============================================================
SAFETY VERIFICATION SUMMARY
============================================================

✓ PASSED: 8
  - Paper Pipeline Unchanged
  - Execution Unchanged
  - Risk Gates Unchanged
  - Frozen Model Intact
  - Adaptive Isolated
  - Retry Guards Active
  - Idempotency Active
  - Config Defaults Safe

============================================================
✓ ALL SAFETY CHECKS PASSED
============================================================
```

### Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Verify Safety Constraints
  run: |
    python3 scripts/rollout/safety_verify.py
    if [ $? -ne 0 ]; then
      echo "Safety verification failed!"
      exit 1
    fi
```

### Checks Performed

#### 1. Paper Pipeline Unchanged

Ensures `paper_gate/*` modules don't import:
- `from app.job_safety`
- `from adaptive`
- `from decision`
- `from leaderboard`

#### 2. Execution Unchanged

Ensures `execution/*` modules don't import:
- `from app.job_safety`
- `from adaptive`
- `from decision`
- `from leaderboard`

#### 3. Risk Gates Unchanged

Ensures `execution_safety/*` modules don't import:
- `from app.job_safety`
- `from adaptive`
- `from decision`
- `from leaderboard`

#### 4. Frozen Model Intact

Checks `config.yaml` to ensure:
- `adaptive.enabled` is `false`
- `adaptive.shadow_learning` is `true` (safe mode)

#### 5. Adaptive Isolated

Ensures `adaptive/*` modules don't have actual import statements for:
- `from execution import ...`
- `import execution`

(Comments are allowed, only actual imports are checked)

#### 6. Retry Guards Active

Verifies:
- `app/job_safety/retry_guard.py` exists
- Contains required methods: `should_execute`, `mark_success`, `mark_completed`
- Config has `retry.max_attempts` and `retry.cooldown_seconds`

#### 7. Idempotency Active

Verifies:
- `app/job_safety/side_effect_guard.py` exists
- Contains required methods: `is_executed`, `mark_executed`, `execute_once`
- Config has `retry.redis.namespace` and `retry.redis.ttl_seconds`

#### 8. Config Defaults Safe

Verifies config.yaml has safe defaults:
- `adaptive.enabled: false`
- `leaderboard.enabled: false`
- `hybrid.enabled: false`

### Maintenance

When adding new safety constraints:

1. Add a new check method to `SafetyVerifier` class
2. Add the check to the `verify_all()` checks list
3. Update this README with the new check documentation
4. Test the check by intentionally breaking the constraint

### Troubleshooting

**Check fails but change looks safe?**

Review the specific error message in the output. The script is intentionally strict to prevent accidental production issues.

**Need to update a protected module?**

Protected modules (`paper_gate/`, `execution/`, `execution_safety/`) should rarely change. If you must modify them:

1. Document the change thoroughly
2. Get peer review
3. Update safety tests
4. Consider if the change could be made elsewhere

**False positive on import check?**

The script checks for actual import statements, ignoring comments. If a comment is flagged, ensure it doesn't contain patterns like `from module import` on the same line.

## Related Files

- `tests/safety/test_full_production_safety.py` - Comprehensive pytest test suite
- `config/config.yaml` - Configuration with safety flags
- `app/job_safety/` - Safety modules being verified

## Support

For issues or questions:
1. Check the output logs for specific failure reasons
2. Review the verification code in `safety_verify.py`
3. Consult the main safety documentation
