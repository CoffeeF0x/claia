# Design Philosophy

This document describes how CLAIA is designed and how work moves through the project. It is written for contributors: read it before proposing a change, and use it to judge whether an idea belongs in the library, in a plugin, or if it doesn't belong at all.

## Principles

### Modules are the unit of work

CLAIA is a collection of modules held together by thin glue. A module is any self-contained capability with a contract — an architecture, a deployment, a solver, an agent, a tool module, or one of the data structures they exchange. Design, implementation, review, and testing all happen at the module boundary.

The framework layer exists to discover modules and route between them. It grows only when modules need a new seam, never as a home for features that could not find a module to live in. A proposal that only makes sense as glue is a proposal worth re-examining.

### Nothing is mandatory

Every module must be usable on its own: constructed directly, without the registry, without plugin discovery, without the process queue. A developer should be able to adopt a single piece of CLAIA without inheriting the rest of it. The framework is a convenience, not a requirement, and any change that makes it a requirement is a regression.

### The core stays small and fenced

Each piece of the core carries one responsibility and an explicit boundary around it. Breadth belongs to plugins; the core provides the contracts that make those plugins interchangeable. When a capability could plausibly live either in the core or in a plugin, it goes in the plugin.

Reference implementations shipped with the library are held to a different standard than plugins: they stay minimal and exemplary, because contributors read them as the model for their own work.

If a piece of the core framework or library becomes, or needs to become, modified in an unintuitive or unreadable way, then that portion of the code should be carefully examined. Both to determine if the code is simply inadequate, or to understand if modification to the overall architecture or design is necessary.

### Contracts before behavior

Modules communicate through stable, explicit structures rather than through assumptions about each other's internals. Changing a contract is a deliberate act with a wider blast radius than changing an implementation, and should be treated as such in design and review.

### Behavior is inspectable

A consumer should always be able to determine why CLAIA did what it did — why a backend was selected, why a call failed, what a module was handed. Convenience that hides the mechanism from the caller is not convenience.

### Consumers do not justify core features

The CLI is CLAIA's first consumer and its living demonstration, not a privileged one. If only the CLI needs something, it belongs to the CLI. The same applies to any other application built on the library.

## Development flow

Every change travels the same path. Stages can be fast, and for a small change most of them are, but they are not skipped.

```
idea -> implementation -> sanity testing -> comprehensive testing -> ci -> deployment testing -> staging -> production
```



### Idea

Establish scope before writing code. Decide which of four things the idea is: a change to a core contract, a module or plugin, a consumer feature, or something CLAIA should decline to do. Declining is a legitimate and common outcome.

### Implementation

Build the module against its contract, and make it work standalone before wiring it into the framework. If it cannot be exercised without the registry, it is not finished.

### Sanity testing

Hands-on human validation. The sanity module/folder under claia is a space for simple validation, and is disposable by design. The code is minimal and readable, and edge cases are explicitly not its concern. It answers "does this behave the way I expect when I use it?" — a simple validation process with an easily modifiable design quickly adapt for your own validation.

The sanity folder is not a comprehensive test suite and must never grow into one.

### Comprehensive testing

The permanent, comprehensive test layer, and the first stage that runs without a human in the loop. Two conventions keep it navigable:

- **Tests mirror the source tree.** A module at `src/claia/core/solvers/default.py` is tested at `src/tests/core/solvers/default.py`. Directory names match, and files carry no `test_` prefix.
- **Shared fixtures, fakes, and builders live in** `src/tests/mocks/`**.** Tests do not define their own, which keeps the structures under test consistent across the suite.

Tests are modular in the same way the source is: each file covers its counterpart's contract and the edge cases the sandbox deliberately ignored.

### CI

The automated pipeline. It runs the test suite and, on success, produces the packages and images the later stages consume. CI is the boundary between a change that works on one machine and a change that works.

### Deployment testing

A post deployment, manual verification step against real artifacts, built outside an active development environment. Testers install the built packages into clean environments and exercise them as a user would, which catches the class of problem that only appears once packaging, dependencies, and installation are involved. This step is necessary for any versioned release.

### Staging

Pre-production validation, where release candidates are available for early testing and inspection.

### Production

The release. If the preceding stages were done honestly, this stage will be uneventful. Which above all else, is the goal of this exaustive pipeline.