# Retirement Income Management System (RIMS)

## PROJECT.md

**Version:** 0.2

---

# Project Mission

Develop a professional software application that assists an income-focused retiree in managing investments by emphasizing sustainable income, dividend safety, and objective portfolio analysis.

RIMS is not intended to predict markets.

RIMS is intended to improve investment decisions.

---

# Product Vision

RIMS shall become the primary management system for an income-oriented retirement portfolio.

The system will integrate portfolio information, historical records, investment research, and advisor interactions into a single decision-support environment.

---

# Primary Objective

Generate dependable retirement income while preserving capital over the long term.

---

# Success Criteria

The software should answer these questions within one minute of opening the Dashboard:

1. Is my retirement income becoming more secure?

2. Has projected annual income increased or decreased?

3. Which investments require attention?

4. What should be discussed with my financial advisor?

---

# Investment Philosophy

The software is built around the following principles.

## Income First

Forward Annual Dividend Income is the primary measure of success.

---

## Total Return Matters

Total return is monitored but is not the primary objective.

---

## Dividend Stability

Dividend reductions deserve greater attention than temporary market price declines.

---

## Objective Decisions

Investment decisions should be supported by measurable facts whenever possible.

---

## Long-Term Perspective

The software supports retirement investing.

It is not intended for trading.

---

# Design Principles

## Single Source of Truth

Charles Schwab is the authoritative source for:

- Holdings
- Market Values
- Cost Basis
- Transactions

RIMS stores only information that Schwab does not maintain.

---

## Separation of Responsibilities

Python performs:

- Importing
- Calculations
- Analysis
- Workbook generation

Excel/Numbers provides:

- Presentation
- Printing
- Review
- Manual notes

Business logic shall not reside in workbook formulas.

---

## Preserve History

Historical information shall never be overwritten.

Monthly snapshots are permanent.

---

## Configuration Driven

Business rules belong in configuration files.

Examples include:

- Portfolio Yield Goal
- Minimum Yield
- Position Limits
- Watch List Rules

---

## Modular Design

Each module has one responsibility.

Modules communicate through well-defined interfaces.

---

# Coding Standards

Python Version

3.12+

Style

PEP 8

Architecture

Object-Oriented Design

Type Hints

Required

Dataclasses

Required

Documentation

Required

Unit Testing

Required for business logic.

---

# Data Model

Core entities include:

Portfolio

Holding

Snapshot

Configuration

Workbook

Watch List

Report

These entities shall evolve independently.

---

# Development Methodology

Development follows a controlled, iterative sprint process.

Each development increment is assigned a sequential sprint number.

Each sprint shall have:

- A clearly defined objective.
- Defined scope.
- Identified files or components affected.
- A complete implementation.
- Defined testing and acceptance criteria.
- Verification before completion.
- Documentation of the completed work.
- A Git commit and push to the repository.

Each sprint should produce one complete, usable artifact or a complete increment toward the current release.

No placeholders.

No incomplete implementations.

Work shall not be considered complete until the defined acceptance criteria have been satisfied.

Sprint numbers are sequential and permanent.

A completed sprint number shall not be reused.

---

# Product Backlog

Future capabilities include:

- Portfolio Health Score
- Advisor Scorecard
- Research & Opportunities
- Stock Rover Integration
- Dividend Calendar
- Retirement Forecasting
- Roth Conversion Planning
- Tax Analysis
- Income Stress Testing
- AI Portfolio Review

Backlog items are intentionally excluded until the core system is complete.

---

# Release Philosophy

A sprint is considered complete when:

- Code executes successfully.
- Tests pass.
- Acceptance criteria are satisfied.
- Documentation is complete.
- Changes are committed to Git.
- Changes are pushed to GitHub.
- The working tree is clean.

A release is considered complete when all sprints required for that release have been completed and the release acceptance criteria have been satisfied.

The Git repository is the authoritative source for the current implementation.

---

# Naming Conventions

Classes

PascalCase

Functions

snake_case

Variables

snake_case

Constants

UPPER_CASE

Modules

lowercase

---

# Documentation Standards

Every module shall begin with:

Purpose

Responsibilities

Dependencies

Revision History

Author

---

# Change Management

Changes are introduced through the controlled sprint and release process.

Every significant development increment receives a sequential sprint number.

Each completed sprint shall be recorded in `CHANGELOG.md`.

Sprint documentation shall identify:

- Sprint number.
- Objective.
- Files changed.
- Implementation.
- Testing.
- Acceptance result.
- Completion status.

Completed work should remain stable unless improvement is justified.

Changes to completed functionality should be treated as new development work and assigned to a subsequent sprint when appropriate.

Sprint numbers shall not be skipped, reused, or reassigned.

---

# Quality Objectives

Readable code.

Maintainable code.

Extensible architecture.

Minimal technical debt.

Professional documentation.

---

# Long-Term Vision

Version 1.x

Retirement Income Management System

Version 2.x

Advanced Portfolio Analytics

Version 3.x

Retirement Income Decision Support System

The software should continue evolving without requiring architectural redesign.

---

# Guiding Principle

When faced with competing alternatives, choose the design that is:

- simpler,
- easier to maintain,
- easier to understand,
- and easier to extend.

Long-term maintainability is more important than short-term convenience.