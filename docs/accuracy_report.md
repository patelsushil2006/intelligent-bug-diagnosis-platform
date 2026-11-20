# Accuracy & Evaluation Report

## Summary Results

| Field | Accuracy | n |
| :--- | :--- | :--- |
| Severity Accuracy | 86.7% | 15 |
| Priority Accuracy | 86.7% | 15 |
| Exception Accuracy | 93.3% | 15 |
| Failure Point Accuracy | 73.3% | 15 |

## Failure Cases

- **gt-06**: Crash with OutOfMemoryError in memory manager cache
  - Failure point mismatch (got: manager.java:34, expected: memorystore.java:82)
- **gt-08**: NullPointerException in auth token verification filter
  - Severity mismatch (got: Medium, expected: High)
  - Priority mismatch (got: P3, expected: P2)
  - Failure point mismatch (got: securitychain.java:30, expected: tokenfilter.java:64)
- **gt-11**: Network Error when fetching user profile data
  - Failure point mismatch (got: unknown:0, expected: views/profile.js:18)
- **gt-14**: Segmentation fault memory crash in proxy engine balancer
  - Exception mismatch (got: unknownerror, expected: sigsegv)
- **gt-15**: Runtime panic nil pointer dereference in gateway handler
  - Severity mismatch (got: Medium, expected: High)
  - Priority mismatch (got: P3, expected: P2)
  - Failure point mismatch (got: /go/src/gateway/main.go:24, expected: /go/src/gateway/server.go:87)
