# Deletion and archival policy

## Purpose

Deletion must not change a production protocol, destroy research data, or
silently remove a reusable definition from another object. The current schema
uses `CASCADE` on many relationships, so a delete can have effects far beyond
the row selected in the editor. This document defines the intended behavior
and records the implementation boundary.

## Implementation status

Safe physical deletion of unused, unlocked definitions is implemented through
the authenticated editor deletion screen and centralized service. The service
rechecks protection and reverse references inside the definition-write mutex
transaction, requires a reason, and writes a durable audit record before
deleting. Direct instance and queryset deletion of top-level definitions must
go through that service. Relationship rows can be detached only while their
owning parent is not protected.

The screen currently supports Studies, Experiments, Forms, Questions, and
Enums. It blocks a Form still in any Experiment, a Question still in any Form,
and an Enum still used by any Question, including when all parents are
unlocked. It also blocks Experiments with Study memberships, sessions,
responses, tickets, notifications, stimulus assignments, attributes, or
files. Cascade cleanup is limited to the target's own relationship rows; child
definitions are not deleted.

Archive/retirement state and filtering are not implemented. Therefore used or
referenced definitions are retained and blocked from deletion; there is not yet
an archive action to retire them. Restrictive foreign keys prevent referenced
definitions from being removed by direct SQL or ORM collector cascades.
Operational/history writers do not all use the definition-write mutex, so a
complete production-backend concurrency audit remains outstanding.

The policy applies to editor actions, imports, admin actions, scripts, jobs,
ORM bulk operations, and future APIs. Hiding a Delete button is not enforcement.

## Core rules

1. **Never delete or modify a locked definition.** A Study lock protects the
   Study, its ordered membership, included Experiments, and their complete
   protocol dependencies. An Experiment lock protects that Experiment and its
   Forms, Questions, Enums, and definition relationship rows. A standalone
   locked Experiment receives the same protection as one in a locked Study.
   Existing standalone Form and Question locks remain protective as well.
2. **Never delete a child that is still referenced by a higher-level
   definition.** For example, a Form cannot be deleted while any
   `ExperimentXForm` references it, even when every referencing Experiment is
   unlocked. A Question cannot be deleted while a `FormXQuestion` references
   it. A DataFormat/enum cannot be deleted while a Question references it.
3. **Detaching is not deleting.** Removing a relationship from an unlocked
   parent may be allowed after checking lock protection and data-retention
   constraints. It removes only that parent's relationship row; it never
   deletes the referenced child. A locked parent relationship cannot be
   detached, reordered, or changed.
4. **Retain research and audit records.** Do not cascade-delete participant
   sessions, responses, tickets, notifications, attached files, exclusions,
   or audit data as a side effect of deleting a definition. Collected data is
   not disposable merely because a definition is no longer used.
5. **Use archival for retirement.** Once a definition has been used in
   collection or referenced by historical data, prefer an explicit inactive or
   archived state over physical deletion. Archive preserves identity and
   historical references while allowing editors to exclude it from new work.
6. **Make deletion conservative, atomic, and explainable.** Preflight the
   complete dependency and cascade graph inside the same transaction and
   synchronization protocol as writes and locks. If any blocker exists, do not
   partially delete anything; tell the user what refers to the object and
   whether detach, archive, or an approved retention procedure is possible.

## Proposed behavior by object

| Object | Physical deletion policy |
| --- | --- |
| **Study** | May be deleted only while unlocked and with no production/history retention requirement. Deleting a Study may remove its own `StudyXExperiment` membership rows, but must never delete its Experiments. A locked Study cannot be deleted. |
| **Experiment** | May be deleted only if unlocked, not included in any Study, and with no sessions, responses, tickets, notifications, group-session records, experiment files, or other retained operational/history records. Any membership in a locked Study blocks deletion independently. If it has been used, archive it instead. |
| **Form** | May be deleted only if it is unlocked, not referenced by any `ExperimentXForm`, and not referenced by retained `Response` rows or other historical records. Participation in even one unlocked Experiment blocks deletion until that relationship is explicitly detached. If historically used, archive it instead. |
| **Question** | May be deleted only if it is unlocked, not referenced by any `FormXQuestion`, and not referenced by retained `Response` rows. A Form relationship must be detached first, and only when that Form's composition is editable. If historically used, archive it instead. |
| **DataFormat / enum** | May be deleted only if no Question references it and it is not protected through a locked dependency graph. Never change enum labels or order in place when historical responses may depend on their positional values; create a distinct format and use it from a new Question. |
| **StudyXExperiment** | May be removed only from an unlocked Study. Removing membership detaches the Experiment; it does not delete it. The Experiment and its definitions remain protected if another locked Study includes it. |
| **ExperimentXForm** | May be removed only from an unlocked, unprotected Experiment. Removing the row detaches the Form; it does not delete the Form. A Form used by historical responses remains retained. |
| **FormXQuestion** | May be removed only from an unlocked, unprotected Form. Removing the row detaches the Question; it does not delete the Question. A Question used by historical responses remains retained. |

“No historical records” must be determined from actual references, not inferred
from a current lock flag. Legacy production data may exist under definitions
that were never marked locked. Inventory those records before allowing deletion.

The reference checks must include all relevant reverse relations, not just the
obvious editor parent. For example, current `Response` rows reference
Experiment, Form, and Question; `Session` references Experiment and Ticket;
Ticket references Experiment; and Notification and file/attribute models can
also reference experiments, sessions, or their definitions. Group-session
models add further dependencies. The exact graph must be re-inventoried when
models change.

## User workflow

- Offer Delete only for objects eligible under the policy. Explain when an
  object is ineligible, rather than presenting a destructive action that will
  fail without context.
- Before deletion, show a confirmation naming the object and a dependency
  summary: parent memberships, child definitions, and operational/history
  records. Do not offer cascade deletion of these dependencies as a shortcut.
- For a referenced child, direct the user to the owning editable parent to
  detach the relationship first. Explain that a relationship change does not
  delete the child and may be blocked by a lock.
- Offer Archive/Retire for used or referenced definitions. Archived objects
  remain resolvable by existing Studies, Experiments, sessions, responses, and
  reports, but are excluded from new selection by default. Any exception to
  that default must be explicit.
- Require an appropriate authenticated editor role for draft cleanup and
  Release manager access for any future archive/retirement action affecting a
  released definition. Account administrators inherit the higher role, but
  must not receive a routine lock bypass.
- Record actor, timestamp, target identity, action, reason, and relevant
  reference counts for deletion and archival events. Hard deletion of
  historical participant data requires a separate, documented retention and
  privacy procedure, not the definition editor.

## Implementation requirements

1. Add a single deletion policy/service that computes blockers and executes an
   allowed delete or archive atomically. Reuse the definition-write mutex and
   protection checks used for lock transitions so a concurrent attach, response
   write, archive, or lock cannot race the preflight.
2. Protect both the selected object and every affected/cascaded object.
   Django's `on_delete=CASCADE`, model `delete()` overrides, and queryset
   deletion do not by themselves guarantee this: collector-driven cascades can
   bypass instance overrides. Queryset `delete()`, bulk operations, admin,
   imports, and future callers must all follow the service. Use restrictive
   database foreign keys (`PROTECT`/`RESTRICT`) for definition and historical
   references where compatible, as defense in depth.
3. Do not treat relationship rows as owned children when deleting a shared
   definition. Delete a relationship only when its parent is permitted to
   change; delete the referenced definition only when it has no remaining
   references and no history.
4. Introduce archive state only with a complete selection-policy review. Keep
   archived objects available for historical rendering, reporting, exports,
   and existing participant sessions. Do not rewrite historical foreign keys
   to a replacement or clone.
5. Inventory existing objects before enforcing the rules: lock status,
   Study/Experiment/Form/Question relationships, response and session history,
   tickets, files, notifications, and cascades. Prepare a remediation report
   for existing orphaned, multiply referenced, and historically used objects.
6. Add tests for every object type and deletion path, including direct instance
   and queryset deletes, cascades, bulk operations, shared references, unlocked
   parent detach, locked parent detach, historical response/session blockers,
   archived-object lookup, and concurrent deletion versus lock/attach/write.
   Assert that a rejected request leaves every row unchanged.

The existing centralized lock guards are a foundation, not complete deletion
coverage. Until the deletion service, reverse-reference checks, cascade
restrictions, and writer tests are implemented, do not expose definition
deletion controls or describe existing deletion as safe.
