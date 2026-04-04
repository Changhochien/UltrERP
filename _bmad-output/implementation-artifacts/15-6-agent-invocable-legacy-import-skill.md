# Story 15.6: Agent-Invocable Legacy Import Skill

Status: ready-for-dev

## Story

As an operator working with an AI agent,
I want the agent to invoke the reviewed legacy-import workflow through a dedicated skill backed by the CLI,
So that the workflow is reusable, guided, and safe across VS Code, Copilot CLI, and coding-agent contexts.

## Acceptance Criteria

**AC1:** Skill wraps the stable CLI rather than reimplementing business logic  
**Given** the legacy import CLI exposes stable subcommands  
**When** the agent loads the legacy-import skill  
**Then** the skill tells the agent which CLI subcommands to run for staging, normalization, canonical import, and validation  
**And** references supporting resources from the skill directory rather than duplicating the import logic in markdown alone

**AC2:** Skill packaging follows supported discovery rules  
**Given** the repository ships a project skill for legacy import  
**When** the skill is installed  
**Then** it lives in a supported skills directory such as `.github/skills/`, `.claude/skills/`, or `.agents/skills/`  
**And** its `SKILL.md` frontmatter includes a matching `name` and a specific `description` that tells the agent when to load it  
**And** any extra scripts or references are linked from the skill instructions using relative paths

**AC3:** Tool permissions stay conservative  
**Given** the skill may invoke terminal commands  
**When** tool permissions are configured  
**Then** shell execution is left unapproved by default or tightly scoped to the reviewed CLI path  
**And** destructive or high-impact import scopes still require explicit operator confirmation  
**And** the skill does not broadly pre-approve arbitrary shell access

**AC4:** Agent workflow is observable and debuggable  
**Given** an operator asks the agent to run part of the import workflow  
**When** the skill is used  
**Then** the agent can read machine-readable validation output from the CLI-backed workflow  
**And** the operator can tell which subcommand ran, with which batch scope, and what the result was

## Tasks / Subtasks

- [ ] **Task 1: Choose the repository skill location and packaging model** (AC2)
  - [ ] Prefer a supported project-skill directory such as `.github/skills/legacy-import/` or `.agents/skills/legacy-import/`
  - [ ] If the team wants to keep content under `erp-skills/`, document the required `chat.skillsLocations` configuration explicitly instead of assuming discovery works automatically
  - [ ] Define the skill name, description, and invocation mode so the agent can discover it reliably

- [ ] **Task 2: Author the `SKILL.md` workflow wrapper** (AC1, AC2, AC4)
  - [ ] Document when to use the skill and which CLI subcommands map to each migration phase
  - [ ] Link any supporting examples, argument templates, or helper scripts with relative paths from the skill directory
  - [ ] Keep import business logic in Python/CLI code and use the skill as orchestration guidance only

- [ ] **Task 3: Define safe tool-permission policy** (AC3)
  - [ ] Decide whether the skill omits `allowed-tools` entirely or scopes it narrowly to reviewed shell usage
  - [ ] Require explicit operator confirmation for destructive scopes such as canonical import over a large tenant/cutoff range
  - [ ] Document why broad shell pre-approval is unsafe for this workflow

- [ ] **Task 4: Validate the skill end to end** (AC1, AC2, AC3, AC4)
  - [ ] Prove the skill can be discovered by the target agent environment
  - [ ] Prove the skill can call the CLI help and validation commands using the documented invocation path
  - [ ] Add a manual or automated check that the skill surfaces machine-readable validation output rather than depending on prose parsing only

## Dev Notes

### Repo Reality

- The repo already has domain knowledge markdown under `erp-skills/`, but the supported agent-skill discovery locations from the current VS Code and Copilot docs are `.github/skills/`, `.claude/skills/`, and `.agents/skills/` unless additional skill locations are configured.
- The CLI should remain the durable implementation boundary. The skill is the workflow wrapper that tells the agent how and when to call it.

### Critical Warnings

- Do **not** bury business logic in `SKILL.md`; keep it in the CLI and referenced resources.
- Do **not** broadly pre-approve shell unless the exact commands and scripts have been reviewed and trusted.
- Do **not** assume `erp-skills/` is auto-discovered as a project skill without explicit configuration.

### Implementation Direction

- Package the skill where the target agent stack will actually discover it.
- Keep the skill narrow: guide the workflow, point to the CLI, and consume structured output.
- Make the skill description specific enough that the agent loads it for import planning/runs but not for unrelated ERP tasks.

### Validation Follow-up

- Confirm the skill directory name matches the frontmatter `name` exactly.
- Confirm supporting files are referenced via relative links inside `SKILL.md` so agents can load them progressively.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 15 / Story 15.6 / FR62
- `docs/legacy/migration-plan.md` - migration phases and severity policy
- `erp-skills/SKILL.md` - current repo-level domain knowledge pattern to compare against
- `backend/domains/legacy_import/` - planned CLI-backed import surface from Stories 15.1-15.5
- `https://code.visualstudio.com/docs/copilot/customization/agent-skills` - supported skill locations, frontmatter, and progressive loading model
- `https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills` - CLI skill packaging, script references, and conservative `allowed-tools` guidance

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story separates durable CLI logic from the agent-facing skill wrapper.
- Story calls out the supported project-skill locations and the non-standard `erp-skills/` discovery caveat.
