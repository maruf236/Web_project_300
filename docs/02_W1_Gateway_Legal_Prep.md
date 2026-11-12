# Week 1 — Gateway & Legal Prep (Owner: Sarwar Hossain)
Covers FR-029..035, SEC-003..007, OR-02, OR-03, OR-11. *Not legal advice; needs independent review. Verify current bKash docs before coding.*

## bKash flow (implement Week 5)
1. Grant token -> cache id_token, refresh before expiry.
2. Create payment (BDT amount, `merchantInvoiceNumber` = our payment-attempt key) -> `bkashURL`.
3. User pays; bKash redirects to our callback with `paymentID`, `status`.
4. Server-side Execute, then Query payment. Only this trusted result counts (FR-033); typed trxID is never proof (AT-10).
5. Idempotency: unique `payment_attempts.attempt_key` and unique `gateway_payment_id`; callback = insert-or-ignore then reconcile (FR-034, AT-11).
6. Scheduled reconciliation of stale pending attempts.
7. Refunds only via finance-approved, audited admin action (OR-03).
Needed: sandbox merchant credentials, callback URL whitelist, refund permission.

## Privacy / audit checklist
- NID/documents: private encrypted storage, short-lived signed URLs, every access logged (SEC-003/004).
- Live location: only to the booked counterparty during an active trip (SEC-005).
- Audit log: actor, action, record, time, reason; append-only (FR-053).
- Retention/legal hold OPEN (SEC-007, OR-09). Bangladesh data-protection and transport rules need legal review (OR-11).
