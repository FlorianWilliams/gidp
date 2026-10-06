# The transactions nobody advertises

**Florian Williams · https://gidp.dev · October 2026**

Most of what happens in an economy is advertised. Jobs are posted, companies are listed, properties go on the market, suppliers publish catalogues. Discovery systems are built on that assumption: someone says what they want, someone else searches for it, software matches them. The most valuable transactions do not work that way.

A company that would sell under the right conditions is not for sale, and saying otherwise would unsettle its staff, its customers and its lenders. An executive who would consider one particular role is not looking, and being seen to look would cost them the job they have. A board recruiting a successor cannot say so, because the announcement is the news. An investor who would participate if a credible lead appeared has no reason to say so publicly, and every reason not to.

In each case the information that would make the person findable is the very information they cannot publish. So the transaction happens through intermediaries who hold both secrets in their heads (bankers, headhunters, the well-connected), or it does not happen at all. Usually it is the second, and neither side ever learns what it missed.

## The idea

Agents are about to be on both sides of this. By agents I mean the software that acts for a person or a company, as opposed to a chat window. It already lives in their CRM, their inbox, their applicant tracking system, and it increasingly talks to other people's software.

If each side's agent holds its principal's conditions privately, something becomes possible that was not before: two agents can determine whether their principals might want to talk, with neither principal publishing anything and neither agent disclosing the conditions it holds.

The pattern is old and has been proven in practice. Anonymous matchmaking, where a mutual interest is revealed only when it is mutual, was described cryptographically in 1985. Financial markets have run a narrow version in production for decades: an indication of interest that omits side and price, an order resting unpublished in a non-displayed venue that "firms up" only when a counterparty appears. Mergers and acquisitions run the same ladder by hand: an anonymised one-page teaser, then a non-disclosure agreement, then the real memorandum, then a non-binding indication.

None of them works over *sets of conditions* between parties who have never heard of each other, across independently operated software, outside a single venue that both sides must trust.

## What the protocol does

**Graduated Interest Disclosure** defines how two agents do that, and its scope ends with the four elements described below.

A principal's conditions live with their agent in a **Standing Interest**: one or more conditional interests, the constraints and exclusions around them, a policy saying what may ever be revealed and under what conditions, and an explicit statement of what the agent is allowed to do. It is never transmitted, not even in encrypted form.

To be findable at all, an agent publishes a **projection**, a description kept impoverished so that it supports retrieval without being invertible. In the worked example, a company exploring a cross-border transaction publishes *strategic transaction · enterprise software · Europe* and nothing else. Its identity is not in it, nor are the amounts, nor even whether it is the buyer or the seller.

Two agents that find each other open a **compatibility session**. They ask each other questions and answer from values that stay home. An agent holding a maximum valuation of 80 million, asked whether a transaction between 50 and 100 million is compatible, can answer without the number leaving. The answers are themselves constrained: an agent may tell the truth, coarsen or decline, but it may never assert something its own values contradict.

If nothing rules the match out, the session produces an **opportunity**, and only then do the questions of identity and terms arise. Each is gated by the principal's own policy, and negotiation is handed off to a different protocol. The protocol stops before commitment on purpose, since its job is to find out whether two parties should be talking; it concludes nothing itself.

## What it does not do

It is neither a marketplace nor a directory, and it does not require anyone to operate it. Nor is it a negotiation protocol, a payment protocol or an identity system: it references those without replacing them. The specification says so at length, because nobody adopts a protocol whose scope grows without notice.

It is also not finished, and its most important open problem is the subject of the next section.

## The problem we have not solved

An agent that answers questions truthfully leaks. Ask whether a transaction between 50 and 60 million works, then 60 to 70, then 70 to 80, then 80 to 90, and watch the answer change: the threshold has been located without a single number crossing the wire. The reference implementation ships that attack, and it finds an 80-million threshold to within 300,000 in eight questions.

The leak follows from the design, so no implementation can remove it: an oracle that never leaks never discriminates, and one that never discriminates cannot support discovery. What can be asked is how to bound what an adversary extracts per unit of effort while leaving enough signal for honest counterparties.

The closest published work solves the neighbouring case. A July 2026 paper from Apple formalises leakage from observed negotiation dynamics and mitigates it with randomised policies, against a *passive* adversary, and it states that adaptive adversaries are future work. Our adversary is the adaptive one: it chooses its next question in light of the last answer.

So the specification states this as an open problem and does not claim a solution. The companion document sets it out formally with the candidate directions: an information budget kept per Standing Interest, minimum granularity, randomised coarsening, economic cost. Measured, the budget and a granularity lattice do bound what a prober learns, while randomised coarsening only slows it down; none of them yet answers the open problem in general. The most interesting one is native to the protocol. Sessions are reciprocal, so making further answers conditional on the questioner answering symmetric questions makes probing cost the prober information about itself. It does not handle an attacker with nothing to protect, which is where it needs work.

## Where this is

This is a first public draft. It is experimental and unfinished, and it is published in order to be attacked. A reference implementation of the bilateral core comes with it, along with a conformance suite and the probing demonstration above.

Any of the following would change it substantially: a demonstration that each vertical needs different mechanics, which would make this a useful pattern rather than a protocol layer; a proof that the leakage cannot be bounded at usable utility, which would make the whole truthful-answer design untenable; or the discovery that principals do not, in fact, hold conditional interests they would formalise. That last assumption is the one most likely to be wrong, and the hardest to test from a desk.

I would rather learn any of those from a reviewer in 2026 than from a failed deployment in 2028.

The specification, the companion note on open problems, the use cases and the code are at https://gidp.dev. Objections are more useful than agreement, and what I would most like to hear is which prior art I have missed.
