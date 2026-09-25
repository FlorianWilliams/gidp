# The transactions nobody advertises

**{{AUTHOR}} · {{CANONICAL_URL}} · September 2026**

Most of what happens in an economy is advertised. Jobs are posted, companies are listed, properties go on the market, suppliers publish catalogues. Discovery systems are built on that assumption: someone says what they want, someone else searches for it, software matches them.

The most valuable transactions are not like that.

A company that would sell under the right conditions is not for sale, and saying otherwise would unsettle its staff, its customers and its lenders. An executive who would consider one particular role is not looking, and being seen to look would cost them the job they have. A board recruiting a successor cannot say so, because the announcement is the news. An investor who would participate if a credible lead appeared has no reason to say so publicly, and every reason not to.

In each case the information that would make the person findable is exactly the information they cannot publish. So the transaction happens through intermediaries who hold both secrets in their heads — bankers, headhunters, the well-connected — or it does not happen at all. Most of the time it does not happen at all, and neither side ever learns what they missed.

## The idea

Agents are about to be on both sides of this. Not the chat window: the software that acts for a person or a company, that already lives in their CRM, their inbox, their applicant tracking system, and that increasingly talks to other people's software.

That opens a possibility that did not exist before. If each side's agent holds its principal's conditions privately, two agents can determine whether their principals might want to talk — without either principal publishing anything, and without either agent disclosing the conditions it holds.

The shape is old and proven. Anonymous matchmaking, where a mutual interest is revealed only when it is mutual, was described cryptographically in 1985. Financial markets have run a narrow version in production for decades: an indication of interest that omits side and price, an order resting unpublished in a non-displayed venue that "firms up" only when a counterparty appears. Mergers and acquisitions run the same ladder by hand — an anonymised one-page teaser, then a non-disclosure agreement, then the real memorandum, then a non-binding indication.

What none of those does is work over *sets of conditions* between parties who have never heard of each other, across independently operated software, outside a single venue that both sides must trust.

## What the protocol does

**Graduated Interest Disclosure** defines how two agents do that. Four things, and nothing else.

A principal's conditions live with their agent in a **Standing Interest** — one or more conditional interests, the constraints and exclusions around them, a policy saying what may ever be revealed and under what conditions, and an explicit statement of what the agent is allowed to do. It is never transmitted. Not encrypted and transmitted: never transmitted.

To be findable at all, an agent publishes a **projection**: a deliberately impoverished description, designed to support retrieval without being invertible. In the worked example, a company exploring a cross-border transaction publishes *strategic transaction · enterprise software · Europe* — and nothing else. Not its identity, not the amounts, not even whether it is the buyer or the seller.

Two agents that find each other open a **compatibility session**. They ask each other questions and answer from values that stay home. An agent holding a maximum valuation of 80 million, asked whether a transaction between 50 and 100 million is compatible, can answer without the number leaving. Answers are constrained: an agent may tell the truth, or coarsen, or decline — it may never assert something its own values contradict.

If nothing rules the match out, the session produces an **opportunity**, and only then do the questions of identity and terms arise — each one gated by the principal's own policy, and negotiation deliberately handed off to a different protocol. The protocol stops before commitment on purpose: it exists to find out whether two parties should be talking, not to conclude anything.

## What it does not do

It is not a marketplace, and not a directory. Nobody operates it by necessity. It is not a negotiation protocol, a payment protocol or an identity system — it references those rather than replacing them, and the specification says so at length, because a protocol that quietly expands its scope is a protocol nobody adopts.

And it is not finished. Which brings us to the part that matters most.

## The problem we have not solved

An agent that answers questions truthfully leaks. Ask whether a transaction between 50 and 60 million works, then 60 to 70, then 70 to 80, then 80 to 90, and watch the answer change: the threshold has been located without a single number crossing the wire. The reference implementation ships that attack, and it finds an 80-million threshold to within 300,000 in eight questions.

This is not an implementation defect. An oracle that never leaks is an oracle that never discriminates, and one that never discriminates cannot support discovery. The real question is how to bound what an adversary extracts per unit of effort while leaving enough signal for honest counterparties.

The closest published work solves the neighbouring case: a July 2026 paper from Apple formalises leakage from observed negotiation dynamics and mitigates it with randomised policies, against a *passive* adversary — and states that adaptive adversaries are future work. Our adversary is the adaptive one, and it chooses its next question in light of the last answer.

So the specification states this as an open problem rather than claiming a solution, and the companion document sets it out formally with the candidate directions, none of them validated. Query budgets, minimum granularity, randomised coarsening, economic cost. The most interesting one is native to the protocol: sessions are reciprocal, so making further answers conditional on the questioner answering symmetric questions makes probing cost the prober information about itself. It does not handle an attacker with nothing to protect, which is exactly where it needs work.

## Where this is

This is a first public draft — experimental, unfinished, and published in order to be attacked. A reference implementation of the bilateral core comes with it, along with a conformance suite and the probing demonstration above.

Three things would change it substantially. A demonstration that each vertical needs different mechanics, which would make this a useful pattern rather than a protocol layer. A proof that the leakage cannot be bounded at usable utility, which would make the whole truthful-answer design untenable. Or the discovery that principals do not, in fact, hold conditional interests they would formalise — which is the assumption most likely to be wrong and the hardest to test from a desk.

I would rather learn any of those from a reviewer in 2026 than from a failed deployment in 2028.

The specification, the companion note on open problems, the use cases and the code are at {{CANONICAL_URL}}. Objections are more useful than agreement, and the most useful thing anyone can tell me is which prior art I have missed.
