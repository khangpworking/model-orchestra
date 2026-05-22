# Test Spec: <feature-name>

Not strict TDD — this is a contract document that drives implementation and verification.

## Happy path

### Test: <name>
- Input: ...
- Expected output: ...
- Notes: ...

## Edge cases

### Test: <name> (empty input)
- Input: ...
- Expected: ...

### Test: <name> (boundary value)
- Input: ...
- Expected: ...

## What should NOT happen

- The function MUST NOT ... (e.g., write to filesystem, mutate input, retry on 4xx)

## Performance / non-functional

- Should complete in <Xms under normal load
- Must handle Y concurrent calls
- Memory ceiling: <Z MB

## Test framework

This project uses: `<jest | vitest | pytest | etc>`. If no runner yet, set one up before implementation.
