# Retirement Income Management System (RIMS)

**Version:** 0.2 (Development)

---

## Overview

The Retirement Income Management System (RIMS) is a Python application that generates an investment management workbook specifically designed for income-oriented retirement portfolios.

Unlike traditional portfolio management software, RIMS is designed around a single objective:

> **Provide a sustainable and growing retirement income while managing investment risk.**

Rather than focusing primarily on market performance, RIMS emphasizes:

- Forward Annual Dividend Income
- Dividend Safety
- Income Stability
- Portfolio Health
- Investment Decision Support

Charles Schwab remains the system of record for holdings and transactions.

RIMS provides the analysis layer.

---

# Project Objectives

The system is designed to answer four questions:

1. Is my retirement income becoming more secure?

2. What requires my attention today?

3. Should I make any portfolio changes?

4. What should I discuss with my financial advisor?

If a feature does not support one or more of these questions, it should not be included in the system.

---

# Design Philosophy

RIMS follows several core principles.

## Income First

The primary metric is:

**Forward Annual Dividend Income**

Portfolio value is important but secondary.

---

## Preserve History

Historical portfolio information is never overwritten.

Monthly snapshots create a permanent investment history.

---

## Objective Decision Making

Watch lists and alerts are generated from objective rules.

The software assists the investor.

It does not make investment decisions.

---

## Single Source of Truth

Charles Schwab remains the authoritative source for:

- Holdings
- Cost Basis
- Market Value
- Share Quantities

RIMS stores only information not maintained by Schwab.

---

## Modular Architecture

Every major capability is implemented as an independent module.

Examples:

- Import
- Dashboard
- Workbook Builder
- Watch List
- Reports
- Charts

This architecture allows future expansion without redesign.

---

# Initial Features

Release 1.0 will include:

- Schwab CSV Import
- Portfolio Object
- Holdings Object
- Workbook Generator
- Dashboard
- Monthly Snapshots
- Configuration
- Watch List
- Release Notes

Future releases will add:

- Portfolio Health Score
- Research & Opportunities
- Stock Rover Integration
- Advisor Review
- Retirement Forecasting
- Income Stress Testing
- Tax Planning

---

# Technology Stack

Language

- Python 3.12+

Libraries

- pandas
- openpyxl
- numpy
- python-dateutil

Development Environment

- Visual Studio Code

Operating System

- macOS

Version Control

- Git
- GitHub

---

# Folder Structure

---

# Development Methodology

The project follows an iterative software development process.

Each release consists of one or more sprints.

Each sprint produces one production-quality artifact.

Every artifact is:

- Complete
- Tested
- Documented
- y for Git commit

---

# Version Roadmap

Release 0.x

Project Foundation

Version 1.x

Core Retirement Income Management System

Version 2.x

Advanced Analytics

Version 3.x

Retirement Income Decision Support System (RIDSS)

---

# Coding Standards

The project follows:

- PEP 8
- Type Hints
- Dataclasses
- Modular Design
- Single Responsibility Principle

Business logic resides in Python.

The Excel workbook is a presentation layer.

---

# Contributing

RIMS is currently developed as a single-user private project.

Development follows a disciplined release process.

Every enhancement must support the project's primary mission:

**Helping retirees make better income-focused investment decisions.**

---

# License

Private.

Copyright © 2026 Timothy Kline.

All Rights Reserved.
