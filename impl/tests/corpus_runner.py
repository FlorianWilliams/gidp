"""Interpreter for the conformance corpus (`conformance/scenarios/*.json`).

The corpus is implementation-independent; this module is the *reference
implementation's* interpreter for it. An independent implementation writes
its own — the grammar is documented in `conformance/README.md` — and the
corpus is the contract between the two.

The interpreter maps each step onto the public Agent API and asserts the
scenario's expectations. It deliberately touches nothing private: if a
scenario cannot be expressed through the public API, that is a finding
about the API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gidp.agent import Agent
from gidp.objects import (
    NEVER,
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
)
from gidp.session import ProtocolError
from gidp.vocab import (
    Authority,
    AuthorityValue,
    ConsentAction,
    Gate,
    SessionState,
    SessionStatus,
    Surface,
)

CORPUS = Path(__file__).resolve().parents[2] / "conformance" / "scenarios"


def _class_of(spec: str) -> DisclosureClass:
    if spec == "never":
        return NEVER
    if spec == "evaluation_only":
        return DisclosureClass(surface=Surface.LOCAL)
    surface, _, gate = spec.partition("/")
    return DisclosureClass(
        surface=Surface(surface),
        gate=Gate(gate) if gate else Gate.NONE,
    )


def _build_agent(name: str, setup: dict[str, Any]) -> Agent:
    policy = {k: _class_of(v) for k, v in setup.get("policy", {}).items()}
    if "conditional_on_policy" in setup:
        policy["conditional_on"] = _class_of(setup["conditional_on_policy"])
    interest = ConditionalInterest(
        action="consider",
        conditions=dict(setup.get("conditions", {})),
        conditional_on=list(setup.get("conditional_on", [])),
    )
    authority = AuthoritySpec(
        levels={
            Authority[level]: AuthorityValue(value)
            for level, value in setup.get("authority", {}).items()
        }
    )
    agent = Agent(
        ref=f"agent:{name}",
        standing_interest=StandingInterest(
            id=f"local:si-{name}",
            principal_ref=f"local:p-{name}",
            interest=interest,
            disclosure_policy=DisclosurePolicy(attributes=policy),
            authority=authority,
        ),
        pre_approved=set(setup.get("pre_approved", [])),
    )
    return agent


def _check(step: dict, payload, label: str) -> None:
    serialised = payload.model_dump_json()
    for needle in step.get("forbid_substrings", []):
        assert needle not in serialised, (
            f"{label}: forbidden substring {needle!r} appears on the wire"
        )


class Corpus:
    def __init__(self, scenario: dict[str, Any]):
        self.name = scenario["scenario"]
        setup = scenario["setup"]
        self.agents = {name: _build_agent(name, spec) for name, spec in setup.items()}
        self._required = {
            name: spec.get("required_dimensions", []) for name, spec in setup.items()
        }
        self.pending_disclosure: tuple | None = None
        self.pending_consent: tuple | None = None
        self.held_ask: tuple | None = None

    def run(self, steps: list[dict]) -> None:
        for i, step in enumerate(steps):
            self._step(step, f"step {i}: {next(iter(step))}")

    # -- steps -------------------------------------------------------------

    def _step(self, step: dict, label: str) -> None:
        a, b = self.agents["A"], self.agents["B"]

        if "open" in step:
            spec = step["open"]
            opened = a.open_session(
                f"corpus-{self.name}",
                purpose=spec["purpose"],
                max_depth=Surface(spec.get("max_depth", "session")),
            )
            a.confirm_accept(b.handle_session_open(opened))
            for name, dims in self._required.items():
                self.agents[name].session.required_dimensions = set(dims)
            return

        if "ask" in step:
            spec = step["ask"]
            asker = self.agents[spec["from"]]
            answerer = b if asker is a else a
            claims = [Claim(**c) for c in spec["claims"]]
            request = asker.ask(claims)
            if spec.get("hold"):
                # The responder receives the question and holds it for a
                # PROBE approval (Section 16.3): no response is produced,
                # and the holder records the unanswered propositions.
                answerer.session.note_unanswered(
                    "received", [c.claim_id for c in request.claims]
                )
                self.held_ask = (asker, answerer, request)
                return
            response = answerer.handle_compatibility_request(request)
            asker.receive_compatibility_response(response, request)
            _check(step, response, label)
            by_id = {o.claim_id: o.result.value for o in response.results}
            for expected in step.get("expect_results", []):
                got = by_id.get(expected["claim_id"])
                assert got == expected["result"], (
                    f"{label}: claim {expected['claim_id']} -> {got}, "
                    f"expected {expected['result']}"
                )
            if "expect_status" in step:
                assert response.session_status.value == step["expect_status"], (
                    f"{label}: reported status {response.session_status.value}, "
                    f"expected {step['expect_status']}"
                )
            return

        if "expire_ask" in step:
            asker, answerer, request = self.held_ask
            self.held_ask = None
            asker.session.expire_request(
                request.request_id,
                claim_ids=[c.claim_id for c in request.claims],
            )
            return

        if "request_disclosure" in step:
            spec = step["request_disclosure"]
            asker = self.agents[spec["from"]]
            answerer = b if asker is a else a
            request = asker.request_disclosure(spec["attribute"], purpose=spec["purpose"])
            if spec.get("hold"):
                self.pending_disclosure = (asker, answerer, request)
                return
            response = answerer.handle_disclosure_request(request)
            asker.session.record_disclosure(response)
            _check(step, response, label)
            if "expect_disclosure" in step:
                assert response.status.value == step["expect_disclosure"], (
                    f"{label}: disclosure {response.status.value}, "
                    f"expected {step['expect_disclosure']}"
                )
            return

        if "release_disclosure" in step:
            asker, answerer, request = self.pending_disclosure
            self.pending_disclosure = None
            response = answerer.handle_disclosure_request(request)
            asker.session.record_disclosure(response)
            if "expect_disclosure" in step:
                assert response.status.value == step["expect_disclosure"]
            return

        if "request_consent" in step:
            spec = step["request_consent"]
            asker = self.agents[spec["from"]]
            answerer = b if asker is a else a
            if step.get("expect_error") or spec.get("expect_error"):
                with pytest.raises(ProtocolError):
                    asker.request_consent(ConsentAction(spec["action"]), spec["scope"])
                return
            request = asker.request_consent(ConsentAction(spec["action"]), spec["scope"])
            response = answerer.handle_consent_request(request)
            asker.record_consent(response)
            answerer.session.record_consent(response, discharge=False)
            self.pending_consent = (asker, answerer, request)
            if "expect_consent" in step:
                assert response.status.value == step["expect_consent"], (
                    f"{label}: consent {response.status.value}, "
                    f"expected {step['expect_consent']}"
                )
            return

        if "principal_answers" in step:
            spec = step["principal_answers"]
            asker, answerer, request = self.pending_consent
            terminal = answerer.principal_answers_consent(request, granted=spec["granted"])
            asker.record_consent(terminal)
            answerer.session.record_consent(terminal, discharge=False)
            return

        if "qualify" in step:
            spec = step["qualify"]
            got = self.agents[spec["role"]].session.qualify()
            assert got is spec["expect"], (
                f"{label}: qualify() -> {got}, expected {spec['expect']}"
            )
            return

        if "state" in step:
            spec = step["state"]
            got = self.agents[spec["role"]].session.state
            assert got is SessionState[spec["expect"]], (
                f"{label}: state {got}, expected {spec['expect']}"
            )
            return

        if "status" in step:
            spec = step["status"]
            got = self.agents[spec["role"]].session.status()
            assert got is SessionStatus(spec["expect"]), (
                f"{label}: status {got.value}, expected {spec['expect']}"
            )
            return

        if "opportunity" in step:
            spec = step["opportunity"]
            from datetime import UTC, datetime, timedelta

            opportunity = self.agents[spec["role"]].session.build_opportunity(
                structure="corpus",
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
                identity_status={},
            )
            _check(step, opportunity, label)
            if "expect_contingent_on" in step:
                assert opportunity.contingent_on == spec["expect_contingent_on"], (
                    f"{label}: contingent_on {opportunity.contingent_on}, "
                    f"expected {spec['expect_contingent_on']}"
                )
            return

        if "handoff" in step:
            spec = step["handoff"]
            agent = self.agents[spec["from"]]
            if step.get("expect_error") or spec.get("expect_error"):
                with pytest.raises(ProtocolError):
                    agent.handoff(spec["target"])
                return
            handoff = agent.handoff(spec["target"])
            other = b if agent is a else a
            other.session.record_handoff(handoff)
            return

        raise AssertionError(f"{label}: unknown step {step!r}")


def scenarios():
    return sorted(CORPUS.glob("*.json"))


def run_scenario(path: Path) -> None:
    scenario = json.loads(path.read_text())
    Corpus(scenario).run(scenario["steps"])
