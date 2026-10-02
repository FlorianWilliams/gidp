# Blind conformance scenarios

Each file is one scenario: a declarative initial state for two parties and
an ordered sequence of steps. Run the steps against your implementation
and report, step by step, everything observable it did. No expected
outcomes are stated anywhere in these files; the comparison is performed
by the evaluator.

## Setup

`setup` declares the two roles (`A` opens the session; `B` responds), in
implementation-neutral terms:

- `conditions`: attribute -> the private value that side holds.
- `policy`: attribute -> its disclosure class, written `surface`,
  `surface/gate`, `evaluation_only` or `never`. An attribute absent from
  `policy` has the specification's default class.
- `authority`: level -> `true` / `false` / `approval_required`. Unset
  levels take the specification's default.
- `conditional_on` (optional): declared dependencies of that side's
  interest. `conditional_on_policy` (optional) sets the disclosure class
  governing them.
- `required_dimensions` (optional): the profile's minimum qualification
  coverage in force for that side.
- `pre_approved` (optional): attributes that side's Principal has
  approved in advance.

## Steps

| Step | What to do |
|---|---|
| `{"open": {"purpose", "max_depth"?}}` | A opens the session, B answers. |
| `{"ask": {"from", "claims": [...]}}` | The named side sends the claims batch; the other side processes it. `hold: true` means the receiving side holds the request for a Principal decision and produces no response. |
| `{"expire_ask": {}}` | The most recently held ask's `expires_at` passes with no terminal response ever sent. |
| `{"request_disclosure": {"from", "attribute", "purpose"}}` | A disclosure request, processed by the other side. `hold: true`: the response is not yet produced. `undelivered: true`: the request leaves the sender and has not reached the other side. |
| `{"release_disclosure": {}}` | The most recently held disclosure request is now answered. |
| `{"request_consent": {"from", "action", "scope"}}` | A consent request, processed by the other side. |
| `{"principal_answers": {"role", "granted"}}` | The named side's Principal decides the outstanding consent. |
| `{"qualify": {"role"}}` | The named side attempts its qualification transition. Report whether it fired. |
| `{"state": {"role"}}` / `{"status": {"role"}}` | Report the named side's session state and its locally computed `session_status`. |
| `{"opportunity": {"role"}}` | The named side builds its Opportunity; report the full serialised object, or the refusal. |
| `{"handoff": {"from", "target"}}` | The named side attempts to emit a Handoff to the target; the other side processes it. Report emissions, refusals, and both sides' resulting states. |

If your implementation refuses to perform a step — refuses to send, to
accept, or to act — that refusal IS the result to report, together with
the rule of the specification you believe requires it. Report also
anything your implementation transmits that the step did not explicitly
ask about.
