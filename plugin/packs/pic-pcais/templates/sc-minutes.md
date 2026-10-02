# {project.short_name} — Steering Committee Minutes — SC-{meeting_number}

<!-- Grounded in the PIC Project Management Guide (May 2025): the Project Lead chairs, takes
     minutes "that include an overall milestone progress update for the project", and distributes
     them to the Steering Committee within five (5) business days of the meeting. The section
     ladder below mirrors the Appendix A standard agenda so minutes answer the agenda one-to-one. -->

**Date/Time:** {meeting.datetime}
**Location / medium:** {meeting.location}
**Chair:** {project_lead.name} ({project_lead.organization})
**Minutes distribution due:** {minutes_due_date}  *(5 business days post-meeting, per MPA)*

## Attendance and quorum

| Name | Organization | Role | Voting | Present |
|---|---|---|---|---|
{attendee_rows}

Quorum per MPA: **{quorum_met}**. PIC representative (non-voting): {pic_pm.name}.

## 1. Approval of previous minutes

{previous_minutes_disposition}

## 2. Project schedule, overview & milestones

<!-- The PM Guide makes this section mandatory in the minutes, not just the agenda. -->
Overall project completion: **{overall_percent_complete}%**

| Milestone | Owner | % complete | Technical progress this period | Status |
|---|---|---|---|---|
{milestone_rows}

## 3. Change orders & change log

Material changes (Change Orders) discussed or decided: {change_orders_summary}
Non-material changes added to the Change Log this period: {change_log_summary}

## 4. Project finances

Spend against forecast: {finance_summary}
Claim status: {claim_status_summary}

## 5. Publications / media

<!-- Advance copies of proposed publications require SC review: 30 days for a publication,
     14 days for an abstract, per the PM Guide. -->
{publications_summary}

## 6. IP update

{ip_update_summary}

## 7. Regulatory check-in

{regulatory_summary}

## 8. Key contact updates

{contact_changes}

## 9. Open discussion / other business / lessons learned

{open_discussion}

## 10. Decisions

| # | Decision | Moved by | Outcome |
|---|---|---|---|
{decision_rows}

## 11. Action items

| # | Action | Owner | Due |
|---|---|---|---|
{action_rows}

## 12. Next meeting

**{next_meeting_datetime}** — calendar holds to be sent within 5 business days.

---
*Recorded by {project_lead.name}. Distributed {distribution_date} per MPA notice requirements.*
