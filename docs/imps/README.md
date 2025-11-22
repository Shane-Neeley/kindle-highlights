# Improvement Proposals (IMPs)

Lightweight decision records for tracking technical decisions, experiments, and learnings across Cozy AI Cafes. IMPs combine ADR simplicity with executable implementation details and AI-friendly context.

## Quick Start

### For Humans and AI Agents

**Creating an IMP:**

```bash
# Find next number
ls docs/imps/IMP-*.md | sort | tail -1

# Create new IMP from template
cp docs/imps/IMP-001-cozy-video-generation-research.md docs/imps/IMP-XXX-your-title.md
```

**Using IMPs for Execution:**

- Check existing IMPs before making changes
- Read code ideas from Implementation section
- Update Learnings as you discover gotchas

**Read IMPs first** to understand patterns and past decisions before implementing features.

**When creating IMPs:**

1. Search codebase with Grep/Glob for context
2. Include exact file paths: `src/services/video.py:320`

## Current Proposals

| ID                                         | Title                     | Status       | Type           | Impact                         |
| ------------------------------------------ | ------------------------- | ------------ | -------------- | ------------------------------ |
| [IMP-001](IMP-001-init.md)                 | Project Overview          | completed    | documentation  | Foundation for all IMPs        |
| [IMP-002](IMP-002-hosted-llm.md)           | Hosted LLM Group Chat API | completed    | infrastructure | 3-way parallel AI chat         |

## When to Write an IMP

Use IMPs for:

- **Technical decisions** affecting architecture or patterns
- **Complex bug fixes** requiring explanation
- **Performance optimizations** with measurable impact
- **New features** requiring design review
- **Experiments** before creating Jira tickets

**Don't use IMPs for:**

- Simple bug fixes (just fix it)
- Dependency updates (use commit message)
- Minor refactoring (use PR description)

Start lean - fill sections as they become relevant.

## IMP Structure

IMPs follow the **Abstract-Decision-Consequences-Implementation** pattern:

### Required Sections

1. **Metadata** - owner, jira ticket, status
2. **Abstract** - One paragraph summary
3. **Motivation & Rationale** - Why this is needed. How it improves the codebase.
4. **Decision** - What we're implementing (specific and actionable)
5. **Consequences** - Positive, negative, risks
6. **Implementation** - File paths, code snippets, logic.
7. **Testing** - How to test the changes. Basic unit test ideas.
8. **Rejected Ideas** - Alternatives considered. These are important, they might lead to a different decision later. Search broadly for ideas.
9. **Tasks** - Checkboxes for tracking progress once execution begins.
10. **References** - Links to Jira, PRs/MRs, packages, docs, blogs, etc.

### Optional Sections

- **Backwards Compatibility** - Migration path
- **Security Considerations** - Security implications
- **Measurements** - Metrics (baseline/target/actual)
- **Learnings** - Updated during implementation

### Status Values

- `draft` - Initial idea
- `accepted` - Ready to implement
- `implementing` - Work in progress
- `completed` - Deployed
- `deprecated` - No longer relevant

## Best Practices

**Writing IMPs:**

- Start with Abstract, Motivation, Decision
- Use specific file paths: `src/services/fileService.js:209`
- **Keep it short**: 1-2 pages max (~250 lines preferred), no full code in Implementation section
- Implementation section: Guidelines only, snippets, not full code
- **Always include Rejected Ideas**: Today's rejected solution may become tomorrow's right answer when context changes
- **Work with existing codebase**: Reuse patterns, functions, maintain coding style, prefer refactoring over rewriting
- Add validation commands: `uv run pytest`
- Document rollback steps

**For AI Agents:**

- Search codebase before writing (Grep/Glob)
- Cite exact line numbers for navigation
- **Don't write full code in IMPs** - provide bullet points and high-level approach only
- IMPs are plans, not implementations
- Cross-reference related IMPs and PRs

**Key principle**: IMPs are decision records + rough implementation guidelines. They should be concise enough that another developer can scan them in 5 minutes and understand the approach without getting lost in code details.

**IMPs are specifications, not implementations:**

- Don't write the actual implementation code in the IMP
- Provide high-level approach and key decisions only
- Basic examples (3-5 lines) are fine to illustrate a concept

## Proven Patterns (From Successful IMPs)

### 1. **Fail Fast, Don't Hide Errors** (IMP-011)

```python
# ❌ BAD: Silent fallback masks problems
try:
    primary_service()
except:
    expensive_fallback()  # Hides root cause, costs money

# ✅ GOOD: Fail loudly, fix the real issue
primary_service()  # Let exceptions surface
```

### 2. **Automate Before You Scale** (IMP-015)

- Test manually once to learn
- Build automated pipeline before running 100+ experiments
- Human review only the shortlist (top 3-5), not everything
- Example: `20 strategies × 4 videos = 80 experiments` → auto-generate → human reviews 12 videos

### 3. **Quantitative Metrics + Human Judgment** (IMP-015)

Metrics narrow the field, humans make final call:

1. **Automated**: SSIM, PSNR, audio RMS → top 5 candidates
2. **Manual**: Watch top 5, pick winner based on feel
3. **Document**: Why winner won (for future reference)

### 4. **Cost Controls Before Production** (IMP-018)

Implement limits BEFORE you need them:

- Daily caps (20 videos/day)
- Budget alerts ($30/month)
- Cost warnings before expensive ops
- Usage tracking from day 1

### 5. **Vertical Motion > Horizontal** (IMP-008, IMP-017)

For seamless loops:

- ✅ **Vertical**: Steam rising, rain falling (exits/enters frame naturally)
- ✅ **Cyclic**: Breathing, swaying (completes full cycle)
- ❌ **Horizontal**: Side-to-side motion (creates edge seams)
- ❌ **Acceleration**: Variable speed (breaks at loop point)

### 6. **Research → Prototype → Validate → Scale** (IMP-013)

1. **Research**: Read papers, competitors, API docs (1-2 days)
2. **Prototype**: Build smallest version that could work (1 day)
3. **Validate**: Test on 3-5 real examples (1 day)
4. **Scale**: Only then build full pipeline
5. **Measure**: Track before/after metrics

### 7. **Status Updates in IMP Headers** (IMP-011)

```markdown
# IMP-XXX: Title

> **Status Update (2025-11-03)**
> ✅ Complete: Feature X working in production
> 🚧 In Progress: Feature Y (blocked on Z)
> ❌ Abandoned: Feature W (reason: too expensive)
```

Keeps IMPs living documents without rewriting whole sections.

## IMP Template

Use [IMP-001](IMP-001-cozy-video-generation-research.md) as a reference example.

```markdown
# IMP-XXX: Title

- owner: shane
- jira: POL-XXXX
- status: draft

## Abstract

One paragraph: problem + solution + impact.

## Motivation & Rationale

- Current problem
- Why now
- Technical constraints

## Decision

What we're implementing (specific and actionable):

- Exact changes
- Technical approach
- Success criteria

## Consequences

### Positive

What gets better?

### Negative

What gets harder?

### Risks

Blurbs about risks, likelihood, impact, mitigation.

## Implementation

### Step 1: Create Service

**File**: `src/services/exampleService.js`

- Add function `doSomething()` that handles X
- Use helper function `validateInput()` for Y
- Return result object with `{ success, data }`

### Step 2: Update Caller

**File**: [src/services/fileService.js:42](../../src/services/fileService.js#L42)

- Import exampleService
- Call `exampleService.doSomething()` with options
- Handle result

### Step 3: Add Tests and Assertions

**File**: `test/unit/services/exampleService.spec.js`

- Test valid input → success
- Test invalid input → error
- Test edge case X

## Tasks

- [ ] Task 1
- [ ] Task 2

## References

- [Jira](https://link)
- [PR](https://link)
```

Note: any docs created along the way, or scripts for testing that are unrelated to main code or test code should be saved to docs/scratchpad folder. Not root.

## Background on IMPs

IMPs combine the best parts of ADRs, RFCs, and PEPs:

- **ADRs**: Context-Decision-Consequences structure
- **RFCs**: Status tracking and collaboration
- **PEPs**: Backwards compatibility and rejected alternatives
- **Modern practices**: Executable code + validation commands

**Key difference**: Living documents that grow during implementation, not static decisions. They do try to be less than 250 lines, but may grow somewhat.

### References

- [ADR GitHub](https://adr.github.io/)
- [MADR](https://github.com/adr/madr) - Markdown ADR templates
- [Staff Engineer's Path](https://www.oreilly.com/library/view/the-staff-engineers/9781098118723/) - RFC templates

---
