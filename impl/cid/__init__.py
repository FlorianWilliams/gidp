"""Reference implementation of Conditional Interest Discovery (CID) 0.1.

This package exists to test the specification, not to ship a product. It
implements the bilateral core under the `core` profile and deliberately omits
multi-party discovery, transport bindings and all cryptography: CID 0.1
requires none of these, and a toy version of any of them would misrepresent
what the protocol guarantees.

It provides no confidentiality against a malicious peer beyond what the policy
layer withholds, and none at all against a malicious operator of this process.
"""

from .vocab import VERSION  # noqa: F401

__all__ = ["VERSION"]
__version__ = "0.1.0"
