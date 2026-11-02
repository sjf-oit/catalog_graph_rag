# SJF Academic Catalog Knowledge Graph
## Executive Overview

**St. John Fisher University | Office of Information Technology**
**Project:** Catalog Graph RAG Pipeline
**Repository:** `sjf-oit/catalog_graph_rag`
**Catalog Year:** 2026–2027

---

## What This Project Is

This project transforms the St. John Fisher University academic catalog into a
**structured knowledge graph** — a database that not only stores catalog information
but explicitly maps every meaningful relationship between the pieces of that information.

The result is a system that can answer questions the current catalog cannot:

- *What courses does a student need to complete the Social Studies concentration
  within the Childhood Education degree?*
- *Which programs are affected if ACCT 101 changes its credit hours?*
- *Who is responsible for maintaining the Nursing program page?*
- *How does the 2026–2027 curriculum differ from 2025–2026?*
- *What requirement groups exist today, and who owns them?*

---

## Why This Matters Now

St. John Fisher is preparing to adopt a new academic catalog product. That transition
will affect every school, every department, and every content owner who maintains
catalog information today.

**The challenge with adopting any new catalog product is that we rarely know in advance:**

- How the new product organizes information internally
- Which parts of our current workflow it will automate
- Which parts will require new processes or manual migration
- What data we need to provide, in what format, to get the system running

Historically, this uncertainty makes catalog product transitions slow, expensive,
and disruptive — because the institution is trying to understand its own current
state *at the same time* it is trying to learn a new system.

**This project addresses that problem directly.**

---

## The Current State of Catalog Data

Today, the SJF catalog is maintained across several disconnected systems and
individual content owners. The information can be broadly grouped into three layers:

### Layer 1 — Courses (from Banner)
Individual course records — course codes, titles, credit hours, descriptions,
prerequisites, and restrictions — originate in Banner, the university's student
information system. The new catalog product will almost certainly import this
layer directly.

### Layer 2 — Pages (from the new catalog product)
Static informational pages — academic policies, degree requirements narratives,
school overviews, tuition information — will be created and managed within
whatever new catalog product is adopted.

### Layer 3 — Everything In Between (currently undocumented)
Between a raw course record and a published catalog page lies a complex web of
relationships that are currently implicit, distributed across content owners,
and nowhere formally documented:

| Undocumented Structure | Example |
|---|---|
| Which courses belong to which degree requirements | HIST 101 is required for the B.A. in History |
| Which degrees offer concentrations or tracks | B.S. Inclusive Childhood Education has a Social Studies track |
| Which minors complement which degrees | Minor in Sustainability complements any undergraduate degree |
| Which department administers which programs | The Accounting department administers the B.S. in Accounting |
| Who owns and maintains each program page | Carolyn Vacca maintains the History program page |
| How requirement groups are structured within a degree | Core Requirements vs. Electives vs. Concentration Requirements |

**This middle layer is where catalog transitions break down.** The new product
will have its own way of organizing this information — and without a clear picture
of how SJF organizes it today, the implementation team will be building from scratch,
negotiating structure with dozens of individual content owners, one department at a time.

---

## What This Project Produces

This project creates a **formal, machine-readable map of the entire middle layer**
by extracting it directly from the current WordPress catalog export.

The knowledge graph captures:

| Object | What It Represents |
|---|---|
| **School** | One of SJF's five collegiate schools |
| **Academic Program** | A department or organizational unit within a school |
| **Program of Study** | A specific credential a student works toward (degree, minor, certificate) |
| **Concentration** | A specialized track within a degree program |
| **Requirement Group** | A named block of required courses within a program or concentration |
| **Course** | An individual course offering with prerequisites |
| **Person** | A content owner responsible for specific catalog pages or programs |
| **Page** | A static informational page scoped to a level and catalog year |
| **Catalog Year** | A specific published edition of the catalog |

Every connection between these objects is explicitly stored — not inferred,
not assumed, not locked inside a content owner's institutional memory.

---

## Why Content Owners Should Care

### You are the source of truth — and that is currently a risk.

Today, the structure of SJF's curriculum lives primarily in the minds of department
chairs, program directors, and catalog coordinators. When a new catalog product
arrives, the implementation team will need to reconstruct that structure from scratch —
interviewing content owners, reviewing old catalog pages, and making judgment calls
about how to map SJF's curriculum into the new system's data model.

This process is slow, error-prone, and places a significant burden on the very
people who are also responsible for keeping the current catalog accurate.

### This project gives you a head start.

By documenting the current structure now — before a new product is selected —
content owners gain several concrete advantages:

**1. A shared reference point for vendor conversations.**
When evaluating a new catalog product, you can ask the vendor directly:
*"Here is how we currently organize programs, concentrations, and requirement groups.
How does your system represent these? What will need to change?"*
That is a much more productive conversation than discovering the answer
during implementation.

**2. A checklist for data migration.**
The knowledge graph provides a complete inventory of every program, concentration,
requirement group, and course relationship in the current catalog. Migration teams
can use this as a checklist to verify that nothing is lost or misrepresented
in the new system.

**3. Visibility into your own content.**
Many content owners maintain their section of the catalog without a clear view
of how it connects to the rest of the institution. The knowledge graph makes
those connections visible — which programs share courses, which departments
have overlapping requirements, which pages are missing content owners.

**4. A baseline for measuring change.**
After the new product is implemented, the knowledge graph provides a documented
baseline of what the catalog looked like before. This makes it possible to
identify what changed, what was lost, and what was improved — rather than
relying on institutional memory.

---

## The Workflow Question

One of the most important questions a new catalog product will force is:

> *Who is responsible for maintaining the information that lives between
> Banner course records and published catalog pages?*

Today, that responsibility is distributed informally across content owners.
The new product may centralize it, automate parts of it, or redistribute it
in ways that are not yet clear.

**Understanding the current workflow — who does what, with what information,
and in what sequence — is essential preparation for that conversation.**

This project documents not just the data structure but the ownership structure:
which departments administer which programs, which individuals own which pages,
and where the boundaries of responsibility currently lie.

That documentation will be invaluable when the institution needs to decide
how to adapt its workflow to a new system — rather than discovering the
workflow by accident during a live implementation.

---

## What Comes Next

This project is designed to be iterative and collaborative. The immediate next
steps are:

1. **Validate the current schema with content owners** — confirm that the
   structure extracted from the WordPress export accurately reflects how
   departments think about their programs and requirements.

2. **Identify gaps and exceptions** — find programs where the current catalog
   page does not fully capture the actual curriculum structure, and document
   those gaps before migration begins.

3. **Extend to prior catalog years** — load 2022–2023 through 2025–2026 to
   create a multi-year view of how the curriculum has evolved.

4. **Use the graph to evaluate vendor proposals** — when catalog product
   vendors present their data models, compare them directly against the
   SJF knowledge graph to identify alignment and gaps.

5. **Support the implementation team** — provide the new catalog product's
   implementation team with a structured, validated export of SJF's current
   curriculum organization, reducing the time spent reconstructing it from scratch.

---

## Technical Summary

The knowledge graph is built using **Neo4j**, an industry-standard graph database,
and populated from the WordPress XML export of the current SJF catalog. The
ingestion pipeline is maintained in this repository and can be re-run against
any catalog year for which a WordPress export is available.

The pipeline is fully open-source, version-controlled, and documented. It does
not require any proprietary tools or vendor dependencies.

---

## Repository Contents

| File | Purpose |
|---|---|
| `load_catalog_from_xml.py` | Primary ingestion pipeline — parses WordPress XML and loads all nodes and relationships into Neo4j |
| `SJF_Catalog_Graph_Schema.md` | Complete technical schema documentation including Mermaid diagram, constraints, and Cypher queries |
| `SCHEMA_PLAIN_LANGUAGE.md` | Non-technical guide to the schema for faculty and administrators |
| `EXECUTIVE_OVERVIEW.md` | This document |
| `requirements.txt` | Python dependencies |
| `.env` | Local credentials (not committed to version control) |

---

*This project is maintained by the St. John Fisher University Office of Information Technology.*
*Questions or contributions: contact the OIT team via the repository issue tracker.*
