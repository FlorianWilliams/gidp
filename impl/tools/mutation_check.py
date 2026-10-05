"""Break the protocol on purpose and see whether the tests notice.

    python tools/mutation_check.py

Coverage says which lines ran. It does not say whether anything would have
failed had those lines been wrong, and a suite can execute every line of a
specification while asserting nothing about it. Each mutation below removes
or inverts one guarantee the specification depends on. A mutation that
*survives* (the suite still passes) marks a guarantee the tests do not defend,
and is a finding about the tests and not about the code.

The mutations are chosen from the properties the specification asks a
conforming implementation to have, and not from whatever happens to be easy
to break.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutation:
    guarantee: str
    file: str
    old: str
    new: str


MUTATIONS = (
    Mutation(
        "a request never carries the requester's own private value (14.3, E-01)",
        "gidp/agent.py",
        "            leaked = self._own_private_value_in(claim)",
        "            leaked = None",
    ),
    Mutation(
        "an identity claim re-reads INTRODUCE at every use (10.6, 16.3, E-02)",
        "gidp/agent.py",
        """            elif claim.key in IDENTITY_ATTRIBUTES and (
                claim.key not in self.consents.identity_revealed
                or self._authority(Authority.INTRODUCE) is AuthorityValue.FALSE""",
        """            elif claim.key in IDENTITY_ATTRIBUTES and (
                claim.key not in self.consents.identity_revealed""",
    ),
    Mutation(
        "an identity disclosure re-reads INTRODUCE at every use (10.6, 16.3, E-02)",
        "gidp/agent.py",
        """            request.attribute not in self.consents.identity_revealed
            or self._authority(Authority.INTRODUCE) is AuthorityValue.FALSE""",
        """            request.attribute not in self.consents.identity_revealed""",
    ),
    Mutation(
        "the responder's reported status gates the initiator (14.6)",
        "gidp/session.py",
        "            and self.peer_status is not None",
        "            and False",
    ),
    Mutation(
        "a Handoff needs a granted consent naming its target (14.7)",
        "gidp/agent.py",
        "        if protocol_ref not in self.handoff_consents:",
        "        if False:",
    ),
    Mutation(
        "a profile's required dimensions block qualification (15.2)",
        "gidp/session.py",
        "            and self.required_dimensions <= covered",
        "            and True",
    ),
    Mutation(
        "an identity claim is declined without reveal_identity (10.6)",
        "gidp/agent.py",
        "            elif claim.key in IDENTITY_ATTRIBUTES and (",
        "            elif False and (",
    ),
    Mutation(
        "no qualifying status is reported while a request is pending (17.2)",
        "gidp/session.py",
        "        if self.state is not SessionState.PROBING:\n            return SessionStatus.OPEN",
        "        if False:\n            return SessionStatus.OPEN",
    ),
    Mutation(
        "session_status is kept after qualification (15.2)",
        "gidp/session.py",
        "        if self.opportunity_emitted:\n            return SessionStatus.POTENTIALLY_COMPATIBLE",
        "        if False:\n            return SessionStatus.POTENTIALLY_COMPATIBLE",
    ),
    Mutation(
        "an identity attribute travels only under reveal_identity (10.6)",
        "gidp/agent.py",
        "        if request.attribute in IDENTITY_ATTRIBUTES and (",
        "        if False and (",
    ),
    Mutation(
        "identity cannot ride disclose_attributes (10.6, 14.5)",
        "gidp/agent.py",
        "        if request.action is not ConsentAction.REVEAL_IDENTITY and any(",
        "        if False and any(",
    ),
    Mutation(
        "qualification defers while a request is pending (17.2)",
        "gidp/session.py",
        "        if self.state is not SessionState.PROBING:",
        "        if False:",
    ),
    Mutation(
        "the responder's stated contingencies reach the Opportunity (14.3, 14.6)",
        "gidp/session.py",
        "        self.note_dependency(*response.contingent_on)",
        "        pass",
    ),
    Mutation(
        "a responder states its communicable contingencies (14.3)",
        "gidp/agent.py",
        "            contingent_on=self.session.own_contingent_on(),",
        "            contingent_on=[],",
    ),
    Mutation(
        "consent under a false authority is declined, not pending (14.5, 16.3)",
        "gidp/agent.py",
        "        if self._authority(level) is AuthorityValue.FALSE:",
        "        if False:",
    ),
    Mutation(
        "a local attribute is never disclosed (9.1, 10.1)",
        "gidp/policy.py",
        "    if cls.surface is Surface.LOCAL:",
        "    if False:",
    ),
    Mutation(
        "COMMIT authority is always false (16.1)",
        "gidp/objects.py",
        "AuthorityValue.FALSE",
        "AuthorityValue.TRUE",
    ),
    Mutation(
        "a session may not go deeper than both sides agreed (14.1)",
        "gidp/policy.py",
        "    if cls.surface.deeper_than(session_depth):",
        "    if False:",
    ),
    Mutation(
        "an answer never contradicts the private values (15.5)",
        "gidp/evaluation.py",
        "    return ClaimResult.COMPATIBLE if evaluation.truth else ClaimResult.INCOMPATIBLE",
        "    return ClaimResult.COMPATIBLE",
    ),
    Mutation(
        "a private threshold is coarsened rather than confirmed (15.4)",
        "gidp/agent.py",
        "        coarsen = evaluation.evaluation_only and evaluation.truth is True",
        "        coarsen = False",
    ),
    Mutation(
        "a response must correlate to a request (14)",
        "gidp/transport.py",
        "            if ref not in self.outstanding:",
        "            if False:",
    ),
    Mutation(
        "a session qualifies only when every claim resolved acceptably (15.2)",
        "gidp/session.py",
        "        if self.status() is not SessionStatus.POTENTIALLY_COMPATIBLE:",
        "        if False:",
    ),
    Mutation(
        "an Opportunity carries its unresolved dependencies (14.6)",
        "gidp/session.py",
        "            contingent_on=self.contingent_on(),",
        "            contingent_on=[],",
    ),
    Mutation(
        "a withheld dependency is not named on the wire (14.3, 14.6, S-23)",
        "gidp/session.py",
        "        if visibility == \"transmit\":",
        "        if True:",
    ),
    Mutation(
        "a result belongs to its proposition, not its dimension (14.2, S-24)",
        "gidp/session.py",
        "            proposition = f\"{direction}:{outcome.claim_id}\"\n            self.results[proposition] = outcome.result",
        "            proposition = outcome.key\n            self.results[proposition] = outcome.result",
    ),
    Mutation(
        "an incompatible result cannot be superseded (14.2, S-24)",
        "gidp/session.py",
        "            if self.results[proposition] is ClaimResult.INCOMPATIBLE:",
        "            if False:",
    ),
    Mutation(
        "a qualifying result never masks a ruled-out claim (15.5, S-25)",
        "gidp/evaluation.py",
        "            if evaluation.truth\n            else ClaimResult.UNKNOWN",
        "            if True\n            else ClaimResult.UNKNOWN",
    ),
    Mutation(
        "a disclosure returns to the stage it was asked in (17.2, S-22)",
        "gidp/session.py",
        "        if target is _RETURN:\n            target = self.return_to",
        "        if target is _RETURN:\n            target = SessionState.PROBING",
    ),
    Mutation(
        "a shape mismatch answers unknown rather than failing (14.2, S-13)",
        "gidp/evaluation.py",
        "        if not all(isinstance(v, Hashable) for v in (*left, *right)):\n            # A range has no membership to intersect. The correct answer is\n            # that this Agent cannot determine one (Section 15.1); raising\n            # would be wrong (see the note on shape mismatches above).\n            return None\n",
        "",
    ),
    Mutation(
        "a held value answers for what it is part of (14.2, S-21)",
        "gidp/evaluation.py",
        "            above = _upward(left, taxonomy)",
        "            above = set(left)",
    ),
    Mutation(
        "approval_required authority forces a pending response (16.2, S-19)",
        "gidp/agent.py",
        "            self._authority(Authority.DISCLOSE) is AuthorityValue.APPROVAL_REQUIRED",
        "            False",
    ),
    Mutation(
        "an audited claim off the lattice is declined (24.3)",
        "gidp/agent.py",
        "            if self.disclosure_audit is not None and not self.disclosure_audit.admits(",
        "            if False and not self.disclosure_audit.admits(",
    ),
    Mutation(
        "a refusal costs nothing, so it is not a channel (24.3)",
        "gidp/auditing.py",
        "        for surviving in outcomes.values():",
        "        for surviving in list(outcomes.values())[:0]:",
    ),
    Mutation(
        "a stated retention must be dischargeable (10.7, S-18)",
        "gidp/agent.py",
        "        if retention is not None and retention not in self.dischargeable_retention:",
        "        if False:",
    ),
)


def run_suite() -> bool:
    """True when the suite passes."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-x",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    print("=" * 88)
    print("Mutation check: does the suite defend what the specification promises?")
    print("=" * 88)
    print()

    if not run_suite():
        print("The suite does not pass unmutated. Fix that first.")
        return 2

    survivors = []
    for mutation in MUTATIONS:
        path = ROOT / mutation.file
        original = path.read_text()
        if mutation.old not in original:
            print(f"  SKIP     {mutation.guarantee}")
            print(
                f"           (anchor not found in {mutation.file}; the mutation "
                "is stale and proves nothing)"
            )
            survivors.append((mutation, "stale"))
            continue
        path.write_text(original.replace(mutation.old, mutation.new, 1))
        try:
            still_passing = run_suite()
        finally:
            path.write_text(original)
        if still_passing:
            print(f"  SURVIVED {mutation.guarantee}")
            survivors.append((mutation, "survived"))
        else:
            print(f"  killed   {mutation.guarantee}")

    print()
    if survivors:
        print(f"{len(survivors)} of {len(MUTATIONS)} mutations were not caught.")
        print("Each is a promise the specification makes and the tests do not keep.")
        return 1
    print(f"All {len(MUTATIONS)} mutations were caught.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
