# CloudSupport — requirements map

| Requirement (BUILD_PROMPTS support) | Test / check | Result |
|---|---|---|
| DNS case + recovery proof | test_dns (gaierror reproduces; localhost resolves) | pass |
| TCP refused + recovery proof | test_tcp (ECONNREFUSED; listener fix; banner OK) | pass |
| HTTP timeout + recovery proof | test_http (0.5s timeout fails; 8s retry 200 + sha256) | pass |
| TLS hostname + recovery proof | test_tls (wrong name CertificateError; right name 200 verified) | pass |
| Upload-expiry + recovery proof | test_upload (expired 403; fresh 200 + hash; tamper stays 403) | pass |
| Automated setup/cleanup | runbook exit 0; servers shut down; temp cert dir removed | pass |
| Evidence per case | test_evidence_shape (symptom..customer_explanation present) | pass |
| No paid cloud / fake certs | LIMITATIONS.md | stated, unclaimed |
