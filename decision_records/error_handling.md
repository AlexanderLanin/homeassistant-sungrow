# 📌 Decision Record: Error Handling Strategy

## Summary

Error handling is a critical component of any robust software system, ensuring that
failures are managed gracefully and that meaningful feedback is provided to both users
and developers. This document defines the error handling strategy for this project,
focusing on **reliability**, **maintainability**, and **user experience**.

## Context

This project operates in **headless environments**, where users cannot simply restart a
script to resolve issues. Consequently, error handling must be more resilient than in a
typical Python application. Failures must be detected, classified, and addressed in a
way that maintains **system stability** and prevents inconsistent states. Since users do
not have direct control over the execution environment, errors must be handled
**automatically and predictably** to ensure continued operation.

As an **open-source project** developed in spare time, the error-handling approach must
also be **practical and maintainable** without introducing unnecessary complexity. The
focus is on **ease of contribution** and ensuring that **debugging remains
straightforward** for developers with limited time.

## Error Classification

Errors in this project fall into three primary categories:

| **Error Type**           | **Frequency**       | **Handling Strategy**                                               |
|--------------------------|--------------------|----------------------------------------------------------------------|
| **Internal Errors**      | Rare               | Fail with a stack trace to aid debugging.                           |
| **Inverter Errors**      | Rare               | Retry communication transparently while maintaining a consistent state. |
| **Communication Errors** | Frequent           | Retry communication transparently while maintaining a consistent state. |

## Error Handling Principles

To ensure **consistent and effective** error management, the following principles guide
our approach:

1. **🛡 Exception Safety:** Errors must not leave the system in an inconsistent or
   undefined state.
2. **🔄 Minimal User Burden:** Where possible, errors should be handled internally,
   reducing the need for error handling code by users.
3. **💬 Clear Feedback:** Users should receive meaningful error messages rather than raw
   stack traces, except where debugging is necessary.
4. **📏 Predictability:** Error handling should be structured, making failure paths easy
   to reason about and recover from.
5. **🛠 Developer-Friendly Maintenance:** Given the nature of open-source contributions,
   the error-handling strategy should be **easy to understand and modify**, ensuring
   that new contributors can make improvements with minimal onboarding effort.

## Evaluation of Error Handling Approaches

### 1️⃣ Exceptions

Exceptions are a widely used error-handling mechanism in many programming languages,
including Python. They allow errors to propagate up the call stack until explicitly
handled. While exceptions provide a **clean separation** between normal and
error-handling code, they introduce challenges in ensuring **predictable and
structured** error management. In large codebases, exceptions can be caught at
inappropriate levels, leading to inconsistent handling and making failure paths
difficult to reason about.

Ensuring **exception safety** requires careful design, as exception-based error handling
can inadvertently leave the system in an inconsistent state if not managed properly.
It's simply difficult to reason about all possible failure paths, which may abort
functions in unexpected ways.

### 2️⃣ Result Types

Result types offer an alternative to exceptions by making error handling **explicit** in
function signatures. This concept, borrowed from languages like **C++
(`std::expected`)** and **Rust (`Result`)**, ensures that every function call explicitly
defines whether it **succeeds or fails**. Instead of raising exceptions, functions
return a value encapsulating either a successful result or an error.

#### **Advantages:**
- **Explicit error handling:** Developers must handle errors at the appropriate level,
  reducing surprises.
- **Improved robustness:** Eliminates unexpected exceptions and allows for safer
  recovery mechanisms.
- **Easier reasoning about failure paths:** The presence of an explicit error type
  clarifies where failures can occur.

#### **Disadvantages:**
- **Increased verbosity:** Functions must explicitly return success or failure values,
  leading to additional boilerplate.
- **Complexity in chaining operations:** Handling multiple levels of failures requires
  additional wrapping and unwrapping logic.
- **Potential friction for contributors:** Developers unfamiliar with result types may
  need to learn a new pattern, adding a slight barrier to entry.

### 3️⃣ Error Codes & Output Parameters

Both approaches are rarely used in Python and are not considered suitable for this
project:

- **Error Codes:** Lead to inconsistent handling patterns and require manual checking,
  increasing the risk of unhandled failures.
- **Output Parameters:** Unidiomatic in Python and introduce unnecessary complexity.

## Decision

To balance **explicit error handling** with **usability**, we adopt a **hybrid
approach**:

- **🔧 Internal Implementation:** Use **result types** for structured and predictable
  error management, ensuring failures are handled explicitly and safely.
- **🚀 Public API:** Raise **exceptions** in user-facing functions to maintain alignment
  with Python’s idiomatic practices.
- **⚙ Handling Strategy:**
  - **Internal Errors:** Fail with a stack trace to aid debugging.
  - **Inverter and Communication Errors:** Retry operations where possible while
    preserving system stability.

This approach ensures that **internally**, the system benefits from the structured
nature of result types, while **externally**, it remains intuitive and familiar to
Python developers.
