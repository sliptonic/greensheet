# Landscape: Existing Tools

Research conducted 2026-09-26. Question: does anything already exist that meets Greensheet's two defining requirements?

1. **Low friction** to start and to use, for both parties.
2. **Asymmetry of action**: one person writes the list, the other can only mark items done and reach out.

Short answer: no single tool does both while also being self-hostable. The closest matches are commercial SaaS. Details below, then the gap, then lessons.

## Categories surveyed

### 1. Client document collection portals

Content Snare, FileInvite, Clustdoc, Intake, File Request Pro, ClientCollect.

| | Asymmetric | Fulfiller friction | Requester friction | Self-host |
|---|---|---|---|---|
| Content Snare | Yes | Low: plain link or magic link, no account | Subscription from $35/mo, no free tier, request builder | No |
| FileInvite | Yes | Low | Subscription, aimed at lenders | No |
| Clustdoc | Yes | Low, with identity verification | From $190/mo, compliance focus | No |
| Intake | Yes | Low: link, no account | Subscription | No |
| File Request Pro | Yes | Low: link, no account | Subscription after trial | No |

These are the closest in **spirit**: a professional sends a client a list of things they need, the client works through it, the professional watches progress and the system nags. Every one of them treats **file upload** as the primary action, with reminders and review/approve loops built around it. They are built for firms with volume, priced accordingly, and none can be self-hosted.

Content Snare is notable for offering exactly the auth model Greensheet chose: plain link or magic link, no client account. That is independent confirmation that D1 is a reasonable design for non-technical fulfillers.

### 2. Shareable checklists with anonymous check-off

| | Asymmetric | Requester sees completion | Fulfiller identity | Self-host | Cost |
|---|---|---|---|---|---|
| CheckFlow | **Yes.** Recipient can complete tasks and fill controls but cannot edit structure, assign, or set dates | Yes, real time | "Anonymous User" via UUID link; optional password | No | $9 to $10 per user per month; anonymous recipients free |
| Checklist Builder Pro | Yes | **No.** Progress is stored in the viewer's browser only | None | No | Free |
| Projoodle | No, everyone edits | Yes | Name typed by participant, no account | No | Free tier |
| The Easy List | No, everyone edits | Yes | None | No | Free |
| opencollective/tasklist | No, everyone edits | Yes | Browser keypair, nostr relays | Single HTML file, but state lives on public relays | Free, open source |

**CheckFlow is the closest behavioral match found.** Creator builds, recipient gets a link, recipient can only complete, creator sees progress live. It differs from Greensheet in being process-oriented (form controls, file uploads, workflow runs), per-seat commercial, cloud-only, and in giving the fulfiller no durable identity: the link is the whole credential, which is the multi-device problem that led to D1.

Checklist Builder Pro is a cautionary example. It is free and asymmetric, but because it has no identity for the viewer, completion state never reaches the creator. It is a personal progress tracker dressed as a shared checklist.

### 3. General task managers with sharing

Todoist, Microsoft To Do, Google Tasks, Trello, Asana, Vikunja, Focalboard.

All of these support sharing and assignment, and all are **symmetric by default**: a person who can see a list can add to it. Todoist's guest role and Microsoft To Do's shared lists both require the guest to hold an account with the vendor. Restricting a collaborator to "complete only" is either unavailable or buried in enterprise permission models. None frames the relationship as one person's expectations of another.

### 4. Household and chore apps

BusyKid, Kikaroo, Chorsee, Neat Kid, ChorePoints, Family Tools; Honeydo Tasks and similar for couples.

The parent-child apps are genuinely asymmetric: parent assigns, child completes from their own login. But they are native mobile apps, require accounts for every family member, and are built around **points, allowance, rewards, and photo proof**. The couples apps are symmetric. None is a general-purpose expectation tool, and none is self-hostable.

### 5. Construction punch lists

PunchPad, CoConstruct, Fieldwire, TaskTag, Digital Foreman Suite.

PunchPad shares live reports with clients and subcontractors without login. The rest are project management platforms. All are domain-specific, most are asymmetric in the sense that the contractor owns the list, and several let the client mark items verified. Heavy, priced for construction firms, not self-hostable.

### 6. Self-hosted open-source onboarding

ChiefOnboarding, Usertour, Laudspeaker.

**ChiefOnboarding** is the only self-hosted, open-source tool found that is asymmetric in the Greensheet sense: an admin assigns to-do items, a new hire completes them through a web dashboard or Slack. It is Python-based, Docker-deployed, AGPLv3. It is also built entirely around the employee-onboarding use case, with sequences, resources, and Slack integration. It is worth a look as a reference for how a Python self-hosted app of this shape is packaged, but it is not something a contractor would send a client.

Usertour and Laudspeaker are product-onboarding and customer-engagement platforms. Different problem.

## The gap

No tool found combines all of:

- Strict asymmetry: one writes, one completes.
- Completion state visible to the requester.
- No account for either party; low-friction identity that survives a device change.
- Self-hosted.
- General purpose, not file collection, not chores, not construction, not HR.
- Items that carry a way to reach the requester about that specific item.

The tools that get closest on behavior (CheckFlow, Content Snare) are commercial cloud services priced for firms. The tools that are free and self-hostable are either symmetric shared lists or single-purpose platforms.

## Lessons for Greensheet

- **Reminders are universal.** Every document-collection tool leads with automated reminders. D5 (opt-in daily digest) is the minimum version of this and is the right call. Expect pressure to add per-item nagging; resist it.
- **Link-only access is the industry norm for the fulfiller side** and it works for people. Magic link (D1) is a strict improvement that at least one major vendor also offers. The decision holds.
- **Identity is what makes completion visible.** Checklist Builder Pro shows what happens without it. Greensheet's Person concept is load-bearing.
- **Every asymmetric tool eventually adds a feedback loop**: approve, reject, "needs a clearer copy," comments. Greensheet's answer is channels. That is a real differentiator and also a real constraint; the spec should keep saying "not a communication channel" out loud.
- **Nobody else has the "flip side" idea.** Every tool surveyed has a fixed owner and a fixed recipient. Anyone-can-be-a-requester (D2, D4) is a genuine difference in framing.
- **Naming matters.** "Checklist," "task list," and "to-do" all pull toward symmetric sharing in users' minds. "Greensheet" as a coined noun helps signal that this is a different object.

## Not surveyed

Form builders (Typeform, Google Forms) and e-signature tools were skipped: they are one-shot submissions, not persistent lists. Kanban tools were folded into category 3.

## Sources

- [Content Snare, official summary](https://contentsnare.com/llms.txt)
- [Content Snare vs Clustdoc, Portico](https://www.portico.run/blog/post/content-snare-vs-clustdoc)
- [Guideflow: document collection software reviewed](https://www.guideflow.com/blog/document-collection-software)
- [Intake](https://intakerequest.com/)
- [File Request Pro](https://filerequestpro.com/)
- [ClientCollect](https://www.clientcollect.com/)
- [CheckFlow: Share a Checklist](https://docs.checkflow.io/docs/checklists/share-a-checklist)
- [CheckFlow pricing](https://www.checkflow.io/pricing)
- [Checklist Builder Pro](https://checklistbuilderpro.com/)
- [Projoodle: shared checklist without login](https://www.projoodle.com/en/checklist-share/)
- [The Easy List](https://theeasylist.com/guides/shared-checklist-without-login)
- [opencollective/tasklist](https://github.com/opencollective/tasklist)
- [Todoist: collaborate with friends or family](https://www.todoist.com/help/articles/collaborate-with-friends-or-family-in-todoist-tzkGUy)
- [Todoist: team roles and access](https://www.todoist.com/help/articles/team-roles-and-access-uGkyLrJQz)
- [Microsoft To Do: share a task list](https://support.microsoft.com/en-us/todo/share-a-task-list)
- [TasksBoard: shared to-do list apps](https://tasksboard.com/blog/shared-to-do-list-app)
- [BusyKid chore charts](https://busykid.com/about-busykid/chore-charts/)
- [Kikaroo chore tracker](https://kikaroo.app/blog/chore-tracker-app/)
- [Chorsee](https://apps.apple.com/us/app/chorsee-chores-tracker/id1611068600)
- [Honeydo Tasks](https://gethoneydo.app/)
- [PunchPad](https://apps.apple.com/us/app/-/id6752496094)
- [CoConstruct punch list](https://www.coconstruct.com/features/construction-punch-list-software)
- [Digital Foreman Suite punch list](https://digitalforemansuite.com/punch-list)
- [ChiefOnboarding](https://github.com/chiefonboarding/ChiefOnboarding)
- [Usertour](https://github.com/usertour/usertour)
- [awesome-selfhosted: task management](https://awesome-selfhosted.net/tags/task-management--to-do-lists.html)
