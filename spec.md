# Digital Evidence Case Tracker · Feature F1: Create Case

This specification defines the rules, examples, acceptance criteria, function interface, and tests for creating a case. It has two layers:

- **Behavior layer:** rules, concrete examples, and acceptance criteria.
- **Technical layer:** pure functions that tests can call without the user interface, storage, or network.

## Traceability

| Source | ID | Text |
|---|---|---|
| User story | S1 | As an investigator, I want to create a case so that I can organize evidence and chain-of-custody records under one case. |
| SRS | REQ-1 | The system shall require a user to authenticate before accessing case information. |
| SRS | REQ-3 | The system shall allow an authenticated Investigator to create a new case. |
| SRS | REQ-4 | The system shall require a case number, title, and status before saving a case. |
| Use case | UC-1 | Create Case |

## Rules

- **R1.** A case number, title, and status are required. A new case begins with the status `Open`.
- **R2.** After outer spaces are removed, a case title must contain 1–100 characters. Exactly 100 characters is allowed.
- **R3.** A case number must be unique after outer spaces are removed and letter case is ignored.
- **R4.** If more than one field is invalid, the system displays every detected error and does not save the case until all errors are corrected.
- **R5.** After a successful save, the system displays `Case created` and a summary containing the saved case number and title.

## Concrete examples

| Rule | Input | Result |
|---|---|---|
| R1 | case number, title, and status are supplied | the required-field check passes |
| R1 | title is blank | the case is rejected with a title-required error |
| R1 | a new case is submitted with status `Closed` | the case is rejected because a new case must begin as `Open` |
| R2 | title contains 25 characters | valid |
| R2 | title contains exactly 100 characters | valid |
| R2 | title contains 101 characters | `Title must be 100 characters or fewer` |
| R3 | `DE-2026-001` exists and the input is ` de-2026-001 ` | duplicate case number |
| R3 | `DE-2026-002` does not exist | valid |
| R4 | only the title is missing | the title error is displayed and the case is not saved |
| R4 | the title is missing and the case number is a duplicate | both errors are displayed and the case is not saved |
| R4 | no fields are invalid | the case is saved |
| R5 | case `DE-2026-002` with title `Evidence Theft` is saved | `Case created` and the case summary are displayed |
| R5 | the save fails because the case number is a duplicate | no success confirmation is displayed |

## Acceptance criteria

| ID | Given | When | Then |
|---|---|---|---|
| F1-AC1 | an authenticated Investigator has entered valid case information | the Investigator submits the Create Case form | the case is saved and `Case created` appears with the saved case number and title |
| F1-AC2 | an authenticated Investigator enters a case title | the system validates the title length | a title containing 1–100 characters is accepted; a title containing 101 or more characters is rejected with `Title must be 100 characters or fewer` |
| F1-AC3 | one or more required fields are blank or contain only spaces | the Investigator submits the case | the case is not saved and an error identifies each missing required field |
| F1-AC4 | case number `DE-2026-001` already exists | the Investigator submits ` de-2026-001 ` | the case is not saved and a duplicate-case-number error appears |
| F1-AC5 | the title is blank and the case number duplicates `DE-2026-001` | the Investigator submits the case | the case is not saved and both the title and duplicate-case-number errors appear |

## Interface

These functions are pure: they do not use the DOM, storage, or network, and they do not change their inputs. Tests call them directly.

- `validateRequiredCaseFields(caseData) → { valid, missingFields }`
  - Returns whether every required field is present and a list of missing fields.
- `validateCaseTitle(title) → "valid" | "required" | "too_long"`
  - Removes outer spaces before checking the 1–100 character limit.
- `isUniqueCaseNumber(caseNumber, existingCaseNumbers) → true | false`
  - Compares case numbers after removing outer spaces and ignoring letter case.
- `validateCreateCase(caseData, existingCaseNumbers) → { valid, errors }`
  - Runs all validation rules and returns every detected error.
- `formatCaseCreatedConfirmation(caseNumber, title) → { message, summary }`
  - Returns the `Case created` message and the saved case number and title for the summary.

### Case data shape

```js
{
  caseNumber: "DE-2026-002",
  title: "Evidence Theft",
  status: "Open",
  description: "Optional case description"
}
```

## Step 9 test cases

Step 9 selects one acceptance criterion: **F1-AC2**, the title-length boundary.

| AC ID | Input | Expected result |
|---|---|---|
| F1-AC2 | `validateCaseTitle("A" repeated 99 times)` | `"valid"` |
| F1-AC2 | `validateCaseTitle("A" repeated 100 times)` | `"valid"` |
| F1-AC2 | `validateCaseTitle("A" repeated 101 times)` | `"too_long"` |
| F1-AC2 | `validateCaseTitle("Evidence Theft")` | `"valid"` |

## Parked question

- The required format for case numbers is not defined in the current SRS and remains parked for a stakeholder decision.

## Out of scope for F1

Adding evidence, recording chain-of-custody entries, reviewing cases, marking cases complete, and generating case summaries are handled by other features.
